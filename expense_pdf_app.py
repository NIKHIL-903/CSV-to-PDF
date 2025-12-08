import streamlit as st
import pandas as pd
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# ---------- PDF GENERATOR ----------

def build_expense_pdf(df: pd.DataFrame) -> BytesIO:
    """
    Takes a DataFrame with columns:
    ['date', 'amount', 'title', 'note', 'category name']
    and returns a BytesIO PDF buffer.
    """
    buffer = BytesIO()

    # Format date as DD-MM-YYYY
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime(
            "%d-%m-%Y"
        ).fillna("")

    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    subtitle_style = styles["Heading3"]

    # Style that allows wrapping
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
    )

    elements = []

    # Title
    elements.append(Paragraph("Expense Report", title_style))
    elements.append(Spacer(1, 12))

    # Total amount
    try:
        total_amount = df["amount"].sum()
        subtitle_text = f"Total Amount: {total_amount:,.2f}"
        elements.append(Paragraph(subtitle_text, subtitle_style))
        elements.append(Spacer(1, 12))
    except Exception:
        pass

    # New column order
    headers = ["Date", "Amount", "Title", "Category", "Notes"]
    table_data = [headers]

    df = df.fillna("")

    for _, row in df.iterrows():
        amount_val = row.get("amount", "")
        if isinstance(amount_val, (int, float)):
            amount_str = f"{amount_val:,.2f}"
        else:
            amount_str = str(amount_val)

        table_data.append([
            Paragraph(str(row.get("date", "")), cell_style),
            Paragraph(amount_str, cell_style),
            Paragraph(str(row.get("title", "")), cell_style),
            Paragraph(str(row.get("category name", "")), cell_style),
            Paragraph(str(row.get("note", "")), cell_style),   # Notes last
        ])

    # Updated column widths
    col_widths = [
        30 * mm,  # Date
        25 * mm,  # Amount
        60 * mm,  # Title
        40 * mm,  # Category
        50 * mm,  # Notes (wider)
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),

        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.whitesmoke, colors.HexColor("#f7f9fc")]),
    ])

    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer



# ---------- STREAMLIT APP ----------

def main():
    st.set_page_config(page_title="CSV to Expense PDF", layout="wide")

    st.title("CSV → Pretty Expense PDF")
    st.write(
        "Upload your CSV file and I’ll generate a clean PDF with only "
        "**date, amount, title, notes, category name**."
    )

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        # Read CSV
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

        st.subheader("Detected Columns")
        st.write(list(df.columns))

        required_cols = ["date", "amount", "title", "note", "category name"]
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(
                f"These required columns are missing in the CSV: {missing}\n\n"
                "Make sure your CSV has columns exactly named: "
                "`date`, `amount`, `title`, `note`, `category name`."
            )
            return

        clean_df = df[required_cols].copy()

        st.subheader("Preview of Data That Will Go to PDF")
        st.dataframe(clean_df.head(20))

        if st.button("Generate PDF"):
            pdf_buffer = build_expense_pdf(clean_df)

            st.download_button(
                label="⬇️ Download Expense PDF",
                data=pdf_buffer,
                file_name="expenses.pdf",
                mime="application/pdf",
            )


if __name__ == "__main__":
    main()
