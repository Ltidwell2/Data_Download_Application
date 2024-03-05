import looker_sdk
from looker_sdk import models40
from looker_sdk.error import SDKError
from PyPDF2 import PdfWriter, PdfReader
from io import BytesIO, StringIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


sdk = looker_sdk.init40("looker.ini")

try:
    me = sdk.me()
except SDKError as e:
    print(f"An error occurred while authenticating with the Looker API. For assistance please contact support@company.com\n\nError: {e}")
    exit()

def run_look_query(look_id, invoice_no, date, limit=10):

    try:
        look_elements = sdk.look(look_id=look_id)
    except SDKError as e:
        print(f"An error occurred while retrieving Look. Error details: {e}")
        exit()
    base_query = look_elements.query

    model = base_query.model
    view = base_query.view
    fields = base_query.fields
    filters = base_query.filters

    # Update filters with specific values
    filters = {
        **filters,
        'lz_header_dtl.invoice_no': invoice_no,
        'calendar_information.date': date,
    }

    # Create a new query
    new_query = sdk.create_query(
        body=models40.WriteQuery(
            model=model,
            view=view,
            fields=fields,
            filters=filters
        ))

    new_query_id = new_query.id

    # Run the query and convert the result to a DataFrame
    result = sdk.run_query(query_id=new_query_id, result_format="json", limit=limit)
    json_io = StringIO(result)
    df = pd.read_json(json_io)

    return df

def run_items_query(i_look_id, invoice_no, date, limit=100):

    items_look_elements = sdk.look(look_id=i_look_id)
    i_base_query = items_look_elements.query

    i_model = i_base_query.model
    i_view = i_base_query.view
    i_fields = i_base_query.fields
    i_filters = i_base_query.filters

    # Update filters with specific values
    i_filters = {
        **i_filters,
        'lz_header_dtl.invoice_no': invoice_no,
        'calendar_information.date': date,
    }

    # Create a new query
    i_new_query = sdk.create_query(
        body=models40.WriteQuery(
            model=i_model,
            view=i_view,
            fields=i_fields,
            filters=i_filters
        ))

    i_new_query_id = i_new_query.id

    # Run the query and convert the result to a DataFrame
    i_result = sdk.run_query(query_id=i_new_query_id, result_format="json", limit=limit)
    json_io = StringIO(i_result)
    idf = pd.read_json(json_io)

    return idf


def create_receipt(df, idf, amt, date, items_purchased, prices, qty, Site_Desc,
                   GPS_Address, GPS_City, GPS_State, GPS_Zip, invoice,
                   account_code,
                   fuel_description, pump_no, pump_qty, pump_price, row=10):
    # Creates a new PDF object
    
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Loads the image and get its dimensions
    logo = ImageReader('logo.png')
    logo_width, logo_height = logo.getSize()

    # Adds the logo to the top of the PDF
    can.drawImage(logo, x=205, y=670, width=logo_width / 18, height=logo_height / 18)

    # Adds the customer address to the PDF
    can.setFont("Helvetica", 12)

    y = 670
    can.drawCentredString(300, y, "Company Inc.")
    can.drawCentredString(300, y - 20, Site_Desc)
    can.drawCentredString(300, y - 40, GPS_Address)
    can.drawCentredString(300, y - 60, f"{GPS_City}, {GPS_State} {GPS_Zip}")

    # Adds the time and invoice number to the PDF
    can.setFont("Helvetica", 12)
    can.drawString(60, y - 80, f"{date}")
    can.drawRightString(500, y - 80, f"Invoice #  {invoice}")

    # Adds the title to the PDF
    can.setFont("Helvetica-Bold", 12)
    can.drawCentredString(300, y - 100, "RECEIPT REPRINT")

    # Adds loyalty information, if it exists
    can.setFont("Helvetica", 12)
    if not pd.isnull(df['lz_loyalty_dtl.account_code'][0]):
        can.drawString(90, y - 120, "Loyalty Club")
        can.drawString(425, y - 120, f"{account_code}")

    # Adds line before beginning fuel/items section
    can.line(50, y - 130, 550, y - 130)

    # Sets the font style for the table header
    if df['lz_fuel_dtl.is_fuel_transaction'][0] == 'Yes':
        can.setFont("Helvetica-Bold", 12)
        can.drawString(50, y - 150, "Fuel Description")
        can.drawString(240, y - 150, "Pump #")
        can.drawString(390, y - 150, "Gallons")
        can.drawString(490, y - 150, "PPG")
        y -= 30
        can.setFont("Helvetica", 12)
        can.drawString(50, y, fuel_description)
        can.drawString(240, y, pump_no)
        can.drawString(390, y, pump_qty)
        can.drawString(490, y, round(pump_price, 2))



    # Sets the font style for the table data
    y -= 170

    if not pd.isnull(idf['lz_merch_pdi_dtl.item_description'][0]):
        can.setFont("Helvetica-Bold", 12)
        can.drawString(50, y - 10, "Item Description")
        can.drawString(390, y - 10, "Qty")
        can.drawString(490, y - 10, "Price")
        # Adds a horizontal line below the table header
        y -= 30
        for i in range(len(items_purchased)):
            can.setFont("Helvetica", 12)
            can.drawString(50, y, items_purchased[i])
            can.drawString(390, y, str(qty[i]))
            can.drawString(490, y, str(round(prices[i], 2)))
            y -= 20

    subtotal = 0
    for i in range(len(prices)):
        subtotal += prices[i] * qty[i]
        total = subtotal

    total = "{:.2f}".format(round(total, 2))
    subtotal = "{:.2f}".format(round(subtotal, 2))

    y -= 10

    can.drawString(290, y, "SUB-TOTAL")
    can.drawString(240, y - 20, "TOTAL PURCHASES")
    can.drawString(490, y, f"${subtotal}")
    can.drawString(490, y - 20, f"${amt:.2f}")

    y -= 20

    # Adds a horizontal line above the total price
    can.line(50, y - 10, 550, y - 10)

    # Adds text to bottom of receipt
    can.setFont("Helvetica-Bold", 12)
    can.drawCentredString(300, y - 90, "RECEIPT REPRINT")
    can.setFont("Helvetica", 12)
    can.drawCentredString(300, y - 110, "THANK YOU FOR")
    can.drawCentredString(300, y - 130, "SHOPPING AT COMPANY")
    can.setFont("Helvetica-Bold", 12)
    can.setFillColorRGB(0, 0, 1)
    can.drawCentredString(300, y - 150, "www.company.com")

    # save the object
    can.save()

    # returns cursor to beginning of pdf object
    packet.seek(0)

    # Read PDF and convert to downloadable output
    new_pdf = PdfReader(packet)
    output = PdfWriter()
    page = new_pdf.pages[0]
    output.add_page(page)

    # Save the PDF content to a BytesIO object
    pdf_bytes_io = BytesIO()
    output.write(pdf_bytes_io)
    pdf_bytes_io.seek(0)

    file_name = "output.pdf"

    with open(file_name, "wb") as pdf_file:
        pdf_file.write(pdf_bytes_io.getvalue())

    return file_name



def receipt_main(invoice_no, date):
    look_id = '1449'
    i_look_id = '1450'
    df = run_look_query(look_id, invoice_no, date)
    idf = run_items_query(i_look_id, invoice_no, date)
    pdf_receipt = create_receipt(df, idf, df['lz_header_dtl.total_amt'][0], str(df['lz_header_dtl.trans_time_time'][0]),
                   idf['lz_merch_pdi_dtl.item_description'].tolist(), idf['lz_merch_pdi_dtl.sell_amt'].tolist(),
                   idf['lz_merch_pdi_dtl.sell_qty'].tolist(), df['organization.site_desc'][0],
                   df['organization.gps_address1'][0], df['organization.gps_city'][0],
                   df['organization.gps_state'][0], df['organization.gps_zip'][0], df['lz_header_dtl.invoice_no'][0],
                   df['lz_loyalty_dtl.account_code'][0],
                   df['lz_fuel_code.description'][0], df['lz_fuel_dtl.pump_no'][0], df['lz_fuel_dtl.pump_qty'][0],
                   df['lz_fuel_dtl.pump_price'][0], df['lz_fuel_dtl.pump_amt'][0],
                   df['lz_fuel_dtl.loyalty_disc_rate'][0], len(df))
    
    return pdf_receipt

if __name__ == "__main__":
    receipt_main(invoice_no = '1302072788', date = '2023-04-01')