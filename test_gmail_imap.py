import sys
sys.path.insert(0, r'C:\Users\lukko\Desktop\projekt zalando\mrowka')
import gmail_imap

accounts = gmail_imap._load_gmail_accounts()
# Testuj z only_unseen=False żeby sprawdzić na mailu 1511
results = gmail_imap.get_new_delivery_emails(accounts[0], only_unseen=False)
print(f"Znaleziono {len(results)} maili dostawczych")
for r in results[-3:]:
    print(f"  konto={r.zalando_account} | order={r.order_number} | tracking={r.tracking} | delivery={r.delivery_date}")
