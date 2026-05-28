MAIN_MENU = (
    "Welcome to KoboSats\n"
    "1. Receive Payment\n"
    "2. Check Balance\n"
    "3. Log Customer Debt\n"
    "4. View My Debts\n"
    "5. Change Language\n"
    "0. Exit"
)

ENTER_AMOUNT = "Enter amount in Naira:\n(e.g. 2500)"

INVOICE_CREATED = (
    "Invoice created!\n"
    "Amount: N{amount_ngn} ({amount_sats} sats)\n"
    "Invoice sent to your phone by SMS.\n"
    "Ask customer to scan and pay."
)

BALANCE = (
    "Your Balance:\n"
    "{sats} sats\n"
    "= N{ngn}\n"
    "Powered by Bitcoin Lightning"
)

DEBT_ENTER_PHONE = "Enter customer phone number:"

DEBT_ENTER_AMOUNT = "Enter amount owed in Naira:"

DEBT_ENTER_DESC = "Enter what it is for:\n(e.g. Rice 5kg)"

DEBT_LOGGED = (
    "Debt logged!\n"
    "Customer: {debtor}\n"
    "Owes: N{amount_ngn}\n"
    "You can send a reminder anytime."
)

DEBTS_LIST_HEADER = "Outstanding Debts:\nTotal: N{total}\n\n"

DEBT_ITEM = "{index}. {phone} - N{amount}\n"

NO_DEBTS = "You have no outstanding debts."

CHOOSE_LANGUAGE = (
    "Choose language:\n"
    "1. English\n"
    "2. Yoruba\n"
    "3. Hausa\n"
    "4. Igbo"
)

LANGUAGE_UPDATED = "Language updated to English.\nDial again to continue."

INVALID_AMOUNT = "Invalid amount.\nPlease enter numbers only.\ne.g. 2500"

INVALID_CHOICE = "Invalid choice.\nPlease try again."

ERROR_GENERIC = "Something went wrong.\nPlease try again."

GOODBYE = "Thank you for using KoboSats!\nPowered by Bitcoin Lightning."