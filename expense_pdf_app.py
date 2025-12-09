import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

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

def build_expense_pdf(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    income_total: float | None = None,
    expense_total: float | None = None,
    net_total: float | None = None,
) -> BytesIO:
    """
    Takes a filtered DataFrame and summary numbers
    and returns a BytesIO PDF buffer.
    """
    buffer = BytesIO()

    # Format date as DD-MM-YYYY for the table
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

    # ----- Heading: Expense Report within that time frame -----
    if start_date and end_date:
        title_text = (
            f"Expense Report ({start_date.strftime('%d-%m-%Y')} "
            f"to {end_date.strftime('%d-%m-%Y')})"
        )
    else:
        title_text = "Expense Report"

    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 12))

    # ----- Summary: income, expense, remaining -----
    if income_total is not None and expense_total is not None and net_total is not None:
        summary_lines = (
            f"<b>Total Income:</b> {income_total:,.2f} &nbsp;&nbsp; "
            f"<b>Total Expense:</b> {expense_total:,.2f} &nbsp;&nbsp; "
            f"<b>Remaining:</b> {net_total:,.2f}"
        )
        elements.append(Paragraph(summary_lines, subtitle_style))
        elements.append(Spacer(1, 12))

    # ----- Table data -----
    # Column order: Date, Amount, Title, Category, Notes
    headers = ["Date", "Amount", "Title", "Category", "Notes"]
    table_data = [headers]

    df = df.fillna("")

    for _, row in df.iterrows():
        amount_val = row.get("amount", "")
        if isinstance(amount_val, (int, float)):
            amount_str = f"{amount_val:,.2f}"
        else:
            amount_str = str(amount_val)

        table_data.append(
            [
                Paragraph(str(row.get("date", "")), cell_style),
                Paragraph(amount_str, cell_style),
                Paragraph(str(row.get("title", "")), cell_style),
                Paragraph(str(row.get("category name", "")), cell_style),
                Paragraph(str(row.get("note", "")), cell_style),
            ]
        )

    # Column widths
    col_widths = [
        30 * mm,  # Date
        25 * mm,  # Amount
        60 * mm,  # Title
        40 * mm,  # Category
        50 * mm,  # Notes
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style = TableStyle(
        [
            # Header style
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            # Body style
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            # Grid + stripes
            ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.whitesmoke, colors.HexColor("#f7f9fc")],
            ),
        ]
    )

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
        "**date, amount, title, category, notes**, plus a summary at the top."
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

        # Parse dates once here
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # ---- Date range filter ----
        min_dt = df["date"].min()
        max_dt = df["date"].max()

        if pd.isna(min_dt) or pd.isna(max_dt):
            st.error("Could not detect valid dates in the 'date' column.")
            return

        st.subheader("Filter by Date Range")
        start_default = min_dt.date()
        end_default = max_dt.date()

        start_date, end_date = st.date_input(
            "Select date range",
            (start_default, end_default),
        )

        # Handle single-date selection case
        if isinstance(start_date, tuple) or isinstance(start_date, list):
            # Just in case Streamlit API differs, but usually it returns 2 values
            start_date, end_date = start_date

        # Ensure order
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
        filtered_df = df.loc[mask, required_cols].copy()

        if filtered_df.empty:
            st.warning("No records in the selected date range.")
            return

        # ---- Summary calculations ----
        amounts = filtered_df["amount"].astype(float)

        income_total = amounts[amounts > 0].sum()
        expense_total = -amounts[amounts < 0].sum()  # make positive
        net_total = amounts.sum()  # income - expense (since expenses are negative)

        st.subheader("Summary for Selected Period")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"{income_total:,.2f}")
        c2.metric("Total Expense", f"{expense_total:,.2f}")
        c3.metric("Remaining", f"{net_total:,.2f}")

        # ---- Preview table ----
        st.subheader("Preview of Data That Will Go to PDF")
        st.dataframe(filtered_df.head(30))

        # ---- Generate PDF ----
        if st.button("Generate PDF"):
            pdf_buffer = build_expense_pdf(
                filtered_df.copy(),
                start_date=start_date,
                end_date=end_date,
                income_total=income_total,
                expense_total=expense_total,
                net_total=net_total,
            )

            st.download_button(
                label="⬇️ Download Expense PDF",
                data=pdf_buffer,
                file_name="expenses.pdf",
                mime="application/pdf",
            )


if __name__ == "__main__":
    main()
