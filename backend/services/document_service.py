"""PDF generation for insurance policy documents using ReportLab."""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_policy_pdf(policy: Any, quote: Any) -> bytes:
    """Generate a policy PDF document and return the raw bytes.

    Parameters
    ----------
    policy : models.Policy
        The purchased policy ORM object.
    quote : models.Quote
        The associated quote ORM object (carries vehicle/driver data).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements: list[Any] = []

    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Title"], fontSize=18, spaceAfter=12
    )
    heading_style = ParagraphStyle(
        "SectionHead", parent=styles["Heading2"], fontSize=13, spaceAfter=6
    )

    # Title
    elements.append(Paragraph("Auto Insurance Policy", title_style))
    elements.append(Spacer(1, 0.15 * inch))

    # Policy overview table
    overview_data = [
        ["Policy Number", policy.policy_number],
        ["Status", policy.status.value.title()],
        ["Coverage Type", policy.coverage_type.value.title()],
        ["Premium Amount", f"${policy.premium_amount:,.2f}"],
        ["Effective Date", str(policy.effective_date)],
        ["Expiration Date", str(policy.expiration_date)],
    ]
    elements.append(Paragraph("Policy Details", heading_style))
    elements.append(_build_table(overview_data))
    elements.append(Spacer(1, 0.2 * inch))

    # Driver info
    driver_data = [
        ["Name", f"{quote.driver_first_name} {quote.driver_last_name}"],
        ["Date of Birth", str(quote.driver_date_of_birth)],
        ["License Number", quote.driver_license_number],
    ]
    elements.append(Paragraph("Driver Information", heading_style))
    elements.append(_build_table(driver_data))
    elements.append(Spacer(1, 0.2 * inch))

    # Vehicle info
    vehicle_data = [
        ["Vehicle", f"{quote.vehicle_year} {quote.vehicle_make} {quote.vehicle_model}"],
        ["VIN", quote.vehicle_vin],
        ["Mileage", f"{quote.vehicle_mileage:,}"],
    ]
    elements.append(Paragraph("Vehicle Information", heading_style))
    elements.append(_build_table(vehicle_data))
    elements.append(Spacer(1, 0.2 * inch))

    # Premium breakdown
    breakdown = quote.premium_breakdown_json or []
    if breakdown:
        bd_data = [["Factor", "Value", "Impact ($)"]]
        for item in breakdown:
            bd_data.append([
                item.get("factor", ""),
                str(item.get("value", "")),
                f"{item.get('impact', 0):+,.2f}",
            ])
        elements.append(Paragraph("Premium Breakdown", heading_style))
        bd_table = Table(bd_data, colWidths=[2 * inch, 2.5 * inch, 1.5 * inch])
        bd_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(bd_table)
        elements.append(Spacer(1, 0.25 * inch))

    # Terms
    elements.append(Paragraph("Terms and Conditions", heading_style))
    terms_text = (
        "This policy is subject to all terms and conditions outlined in the "
        "master insurance agreement. Coverage is contingent upon the accuracy "
        "of the information provided during the quoting process. Any material "
        "misrepresentation may void the policy. This policy provides coverage "
        "for the named vehicle and driver only. Changes must be reported within "
        "30 days. Cancellation is subject to the standard refund schedule."
    )
    elements.append(Paragraph(terms_text, styles["BodyText"]))

    doc.build(elements)
    return buf.getvalue()


def _build_table(data: list[list[str]]) -> Table:
    """Build a two-column key/value table with standard styling."""
    table = Table(data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table
