### RevolVer

Revolut doesn't provide an option to export transactions with custom categories directly. This script replicates the HTTP requests made by the Revolut web application to retrieve transaction data, and export it to SQLite and/or Excel file.

### RevolVer

Revolut doesn't provide an option to export transactions with custom categories directly. This script replicates the HTTP requests made by the Revolut web application to retrieve transaction data, and export it to SQLite and/or Excel file.

### Installation

1. Clone this project  
2. Install the package:
   ```bash
   pip install .
   ```
   *Alternatively, you can still install dependencies from `requirements.txt`:*  
   `pip install -r requirements.txt`

### Requirements
Before each usage, authentication data must be provided. The script supports two methods:

#### Method 1: Copy as cURL (Recommended)
1. Go to https://app.revolut.com and login.
2. Open developer tools by pressing F12.
3. Click on "See all" transactions.
4. In the Network tab, find the request to `transactions/last` endpoint, right-click it and select "Copy > Copy as cURL (bash)" or "Copy as cURL (cmd)".
5. Paste the copied curl command into `curlcmd.txt` file in the root directory.
6. Proceed by running the script right away as the authentication data tend to expire fast.

**Note on Joint Accounts:** Joint accounts are supported via the cURL method. The script will automatically detect the `accountType=joint` and `walletId` from the cURL command.

#### Method 2: HAR file (Legacy)
Alternatively, you can export a HAR file from Revolut web application and save it to `consume/` directory as `app.revolut.com.har`. The script will automatically detect and use it if `curlcmd.txt` is not present.

*Note: HAR method currently does not support Joint accounts as reliably as cURL.*

### Usage

If you installed the package, you can run it directly:
```bash
revol-ver -d 2024.4
```

Otherwise, run the script with:
```bash
python revol_ver.py -d 2024.4
```

At minimum, only `--date` must be provided to fetch results for single month and save them to both SQLite and Excel file.

For initial export, you may want to export all records. Set `--period` to `all`. Also make sure to edit setting `AllImportLookBackYears` in config.ini to desired export period.  
`revol-ver -p all`  

By default, it will save the transactions to SQLite database with filename `trans_db.sql` and Excel file to `exports/` directory. Change this by setting `--output` to either `db` or `excel`.  
`revol-ver -p all -o excel` 

### Development

This project uses `pytest` for testing and GitHub Actions for CI/CD.

**Running tests locally:**
```bash
pip install .[test]
pytest
```

**CI/CD:**
A GitHub Action is configured to:
1. Run the test suite on every push and pull request.
2. Build and package the code into `dist/` artifacts.

### Common errors
...

1. **curl command or HAR file not found**  
`FileNotFoundError: [Errno 2] No such file or directory: 'curlcmd.txt'`  
or  
`FileNotFoundError: [Errno 2] No such file or directory: 'consume\\app.revolut.com.har'`

    Reason and fix: The script needs authentication data. Either:
    - Create `curlcmd.txt` in the root directory and paste a curl command (copied from browser DevTools), OR
    - Export HAR file to `consume/app.revolut.com.har`
  
2. **Token expired**  

    ```
    Exception: Fetching failed, got response  
    {'message': 'Access token expired', 'code': 9039}  
    ```

    Reason and fix: Authentication data has expired. Copy a fresh curl command or export a new HAR file and try again.  

3. **Custom category not defined**
   ```
   Exception:
   Category with ID aead2528-4b7b-481d-bc1f-0f27ec4b3926 was not found. Full transaction:
   ValidationInfo(config={'title': 'TransactionModel'}, context=None, data={'id': '66xxxxab-0e30-axxe-8cc6-791xxxxxxx4b', 'legId': '66xxxxab-0e30-axxe-0000-791xxxxxxx4b', 'type': 'CARD_PAYMENT', 'state': 'COMPLETED', 'startedDate': datetime.datetime(2024, 8, 2, 15, 44, 10), 'updatedDate': datetime.datetime(2024, 8, 3, 13, 13, 38, 150000), 'completedDate': datetime.datetime(2024, 8, 3, 13, 13, 38, 149000), 'createdDate': datetime.datetime(2024, 8, 2, 15, 44, 11, 198000), 'currency': 'EUR', 'amount': -1213.0, 'fee': 0.0, 'balance': 9999.0, 'description': 'Merkur Lj. Vizmarje', 'tag': 'shopping'}, field_name='category')
   ```

    Reason and fix: The script refuses to proceed if Revolut transaction with custom category is not defined in `config.ini`. To fix this specific example, an entry with UUID and custom category name must be added to `custom.categories` section of file `config.ini`:

    ```
    [custom.categories]
    aead2528-4b7b-481d-bc1f-0f27ec4b3926 = home_improvements   
    ```

    With custom categories configured, the script will use this mapping to transform the UUID returned by Revolut to defined category name which is visible in column `category` in both database table and Excel.