# 🧠 Google Places Enrichment Tool

**Enrich any list of companies with real-time business details (phone number, website domain, and full address) using the Google Places API.**

This tool supports both `.csv` and `.xlsx` input/output files, and is optimized for use within data, sales, operations, or engineering teams.

---

## 📌 What It Does

Given an input file (CSV or Excel) with a column like `Company Name`, this script will:

✅ Find matching companies via Google Places  
✅ Fetch:
- Phone Number  
- Website Domain  
- Street Address  
- City  
- Zip Code  
- Country  

✅ Add those fields to a new enriched file

---

## 📁 Folder Structure

.
├── google_places_enrichment.py # The main script
├── .env # Your API key (optional, see setup)
├── input/ # Place your input files here
├── output/ # Enriched files will be saved here
└── README.md # This file

## ⚙️ Requirements

Python ≥ 3.7

Install once via:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Or, install manually:

pip install pandas openpyxl requests tqdm
💡 This project uses pandas for Excel support and requests for API calls.

🔑 Google API Key
To use the Google Places API, you need a valid key with access to:

Places API

Places Details API

Option A: Use .env file (Recommended)
Create a .env file at the root with this content:

GOOGLE_API_KEY=your-real-google-api-key-here

Then load it in your terminal:

export $(cat .env | xargs)

To confirm:

echo $GOOGLE_API_KEY

Option B: Pass the API key inline via CLI:

--api-key YOUR_API_KEY

🧪 Example: How to Run

✅ With CSV input/output:

 python google_places_enrichment.py \
  --input input/companies.csv \
  --output output/enriched_companies.csv \
  --region de \
  --context "City,Country"

✅ With Excel input/output:

python google_places_enrichment.py \
  --input input/companies.xlsx \
  --output output/enriched_companies.xlsx \
  --region de \
  --context "City,Country"

🗂️ Input File Format
Your input file must contain a column like Company Name.

Optional but highly recommended:
- City
- Country

These improve accuracy by helping disambiguate results.

Example:

| Company Name | City          | Country |
| ------------ | ------------- | ------- |
| Tesla        | Berlin        | Germany |
| Google       | Mountain View | USA     |
| BMW          | Munich        | Germany |

📝 Output Fields
Each output file will include:

- phone_number
- domain
- street
- city
- zip_code
- country
- status (OK, PARTIAL, NOT_FOUND, or ERROR)

🚦 Status Codes Explained

| Status       | Meaning                                                  |
| ------------ | -------------------------------------------------------- |
| `OK`         | At least one enrichment field was successfully retrieved |
| `PARTIAL`    | Company found, but only some fields could be filled      |
| `NOT_FOUND`  | No match found in Google Places                          |
| `ERROR:...`  | Exception raised (e.g. network timeout, API quota issue) |
| `EMPTY_NAME` | The company name field was missing or blank in that row  |

🌍 Region Support
Use the --region flag to bias results to a specific country. Examples:

--region de → Germany

--region us → United States

This helps when company names are generic or used globally.

⏱️ Throttling
Default delay between API calls is 0.1s. Adjust with:

--sleep 0.2

Be mindful of Google API quota limits.

🧼 Clean Shutdown
Press Ctrl+C at any time to gracefully stop the script. All rows processed so far will still be saved to output.

📦 Deployment Notes for Engineering
- Python dependencies are isolated using venv
- Codebase supports both .csv and .xlsx I/O
- All fields are handled with fallbacks and error handling
- Easily extensible to support more fields like rating, business status, etc.

🔒 Security / API Key Tips
- Never commit .env files or keys into GitLab
- Use GitLab CI/CD secrets for automation
- Rotate API keys periodically and set quota alerts in Google Cloud Console

✅ Best Practices
- Always include City and Country if available — it improves hit rate
- Use .xlsx for better Excel compatibility unless automation prefers .csv
- Run large batches overnight if API quota is limited
