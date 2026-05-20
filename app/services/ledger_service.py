from datetime import datetime
from app import db
from app.models import StockMovement, MasterItem, PeriodLock, MovementType, ActivityLog

class LedgerService:
    
    @staticmethod
    def check_period_lock(date_to_check):
        """Memeriksa apakah tanggal transaksi berada di periode bulan/tahun yang sudah dikunci."""
        lock = PeriodLock.query.filter_by(
            year=date_to_check.year, 
            month=date_to_check.month, 
            is_locked=True
        ).first()
        if lock:
            raise ValueError(f"Transaksi ditolak. Periode {date_to_check.strftime('%B %Y')} sudah dikunci (Closed Period).")

    @staticmethod
    def record_movement(item_id, movement_type, qty, user_id, document_date=None, supplier_id=None, reference_number=None, notes=None):
        """
        Core Engine Ledger:
        1. Validasi Period Lock.
        2. Validasi Stok agar tidak minus (khusus untuk OUT / Pemakaian / Penjualan).
        3. Gunakan strategi SELECT FOR UPDATE untuk mencegah Race Condition (Stok Tabrakan).
        4. Mutasi kolom cache current_stock di tabel MasterItem.
        5. Catat baris transaksi baru di StockMovement (Double-entry principle style).
        """
        if qty <= 0:
            raise ValueError("Kuantitas transaksi harus lebih besar dari 0.")
            
        doc_date = document_date if document_date else datetime.utcnow().date()
        
        # 1. Validasi Penguncian Periode Akuntansi/Stok
        LedgerService.check_period_lock(doc_date)
        
        # 2. Ambil data barang & Kunci baris di DB menggunakan SELECT FOR UPDATE (Mencegah Race Condition)
        item = db.session.query(MasterItem).filter_by(id=item_id).with_for_update().first()
        if not item:
            raise ValueError("Barang tidak ditemukan dalam sistem master.")
            
        stock_before = item.current_stock
        
        # 3. Hitung efek mutasi stok
        if movement_type in [MovementType.IN, MovementType.ADJUSTMENT] or (isinstance(movement_type, str) and movement_type in ['IN', 'ADJUSTMENT']):
            actual_type = MovementType.IN if (movement_type == MovementType.IN or movement_type == 'IN') else MovementType.ADJUSTMENT
            stock_after = stock_before + qty
        elif movement_type in [MovementType.OUT] or (isinstance(movement_type, str) and movement_type == 'OUT'):
            actual_type = MovementType.OUT
            stock_after = stock_before - qty
            # Pencegahan Stok Minus secara Hard-coded di level Back-end
            if stock_after < 0:
                raise ValueError(f"Transaksi gagal. Stok saat ini untuk '{item.name}' hanya {stock_before}, kurang untuk pengeluaran sebesar {qty}.")
        else:
            raise ValueError("Tipe mutasi stok tidak valid.")
            
        # 4. Update kolom cache di tabel MasterItem
        item.current_stock = stock_after
        
        # 5. Buat baris historis di tabel StockMovement (Buku Besar Stok)
        movement = StockMovement(
            item_id=item.id,
            movement_type=actual_type,
            qty=qty,
            stock_before=stock_before,
            stock_after=stock_after,
            document_date=doc_date,
            supplier_id=supplier_id,
            reference_number=reference_number,
            notes=notes,
            created_by=user_id
        )
        db.session.add(movement)
        
        # 6. Catat log aktivitas user demi audit trail skripsi
        log = ActivityLog(
            user_id=user_id,
            action=f"MUTASI_{actual_type.value}",
            description=f"Mutasi {qty} {item.unit} untuk barang {item.name}. Stok {stock_before} -> {stock_after}."
        )
        db.session.add(log)
        
        return movement

    @staticmethod
    def void_movement(movement_id, user_id, reason="Void transaksi"):
        """
        Fungsi VOID (Pembatalan Transaksi Ledger):
        Membatalkan transaksi salah input tanpa menghapus baris data asli (Audit Trail Preservation).
        Menembakkan saldo balik ke arah sebaliknya.
        """
        # Ambil transaksi asli yang mau di-void
        orig_move = db.session.query(StockMovement).filter_by(id=movement_id).with_for_update().first()
        if not orig_move:
            raise ValueError("Data transaksi asal tidak ditemukan.")
        if orig_move.is_void:
            raise ValueError("Transaksi ini sudah pernah di-void sebelumnya.")
            
        # Cek apakah periode transaksi asal sudah dikunci
        LedgerService.check_period_lock(orig_move.document_date)
        
        # Ambil master item terkait
        item = db.session.query(MasterItem).filter_by(id=orig_move.item_id).with_for_update().first()
        stock_before = item.current_stock
        
        # Balikkan arah saldo stok
        if orig_move.movement_type == MovementType.IN:
            stock_after = stock_before - orig_move.qty
            if stock_after < 0:
                raise ValueError(f"Void gagal. Membatalkan barang masuk ini menyebabkan stok '{item.name}' menjadi minus ({stock_after}).")
        elif orig_move.movement_type == MovementType.OUT:
            stock_after = stock_before + orig_move.qty
        else:
            raise ValueError("Tipe transaksi ini tidak dapat di-void secara otomatis.")
            
        # Update Master stok barang
        item.current_stock = stock_after
        
        # Tandai transaksi asal sebagai Voided
        orig_move.is_void = True
        
        # Buat baris penyeimbang (Contrathing Ledger Entry)
        void_entry = StockMovement(
            item_id=item.id,
            movement_type=MovementType.VOID,
            qty=orig_move.qty,
            stock_before=stock_before,
            stock_after=stock_after,
            document_date=datetime.utcnow().date(),
            reference_number=f"VOID-{orig_move.id}",
            notes=f"{reason} | Referensi ID: {orig_move.id}",
            created_by=user_id,
            void_reference_id=orig_move.id
        )
        db.session.add(void_entry)
        
        # Catat Log Audit Trail
        log = ActivityLog(
            user_id=user_id,
            action="VOID_TRANSAKSI",
            description=f"Melakukan VOID pada transaksi ID:{orig_move.id} untuk barang {item.name}."
        )
        db.session.add(log)
        
        return void_entry