#!/usr/bin/env python3
# **************************************************************************** #
#                                                                              #
#                                                        ::::::::   ::::::::   #
#    export_commands.py                                :+:    :+: :+:    :+:   #
#                                                     +:+        +:+           #
#    By: Ser Superior <marcioeduine@gmail.com>       +#++:++#++ +#++:++#++     #
#                                                          +#+        +#+      #
#    Created: 2026/07/09 10:25:00 by Ser Superior  #+#    #+# #+#    #+#       #
#    Updated: 2026/07/09 20:22:00 by Ser Superior  ########   ########         #
#                                                                              #
# **************************************************************************** #
"""Serialização de resultados de tabelas/queries para CSV, JSON e PDF."""

import sqlite3
import csv
import json

# Attempt to load ReportLab modules safely for native vector PDF render workflows
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def handle_export_command(cursor: sqlite3.Cursor, parts: list) -> None:
    """Serialises database records into flat structured external files safely."""
    if len(parts) < 4:
        print("Error: Invalid syntax. Usage: export <csv/json/pdf> <filename> <table_name/raw_query>")
        return

    export_format = parts[1].lower()
    target_file = parts[2]
    payload_source = " ".join(parts[3:])

    # Enforce standard file extensions if missing from user input
    if export_format == "csv" and not target_file.lower().endswith(".csv"):
        target_file += ".csv"
    elif export_format == "json" and not target_file.lower().endswith(".json"):
        target_file += ".json"
    elif export_format == "pdf" and not target_file.lower().endswith(".pdf"):
        target_file += ".pdf"

    query = payload_source if payload_source.strip().upper().startswith("SELECT") else f"SELECT * FROM {payload_source};"

    try:
        cursor.execute(query)
        if cursor.description is None:
            print("Error: The targeted query source did not output any structured database fields.")
            return

        headers = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()

        if export_format == "csv":
            _export_csv(target_file, headers, records)
        elif export_format == "json":
            _export_json(target_file, headers, records)
        elif export_format == "pdf":
            _export_pdf(target_file, headers, records)
        else:
            print(f"Error: Format option '{export_format}' is currently unsupported. Use 'csv', 'json' or 'pdf'.")
    except Exception as error:
        print(f"Export processing collapsed: {error}")


def _export_csv(target_file: str, headers: list, records: list) -> None:
    """Serialises the result set into a flat CSV stream."""
    with open(target_file, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(records)
    print(f"Success: {len(records)} rows exported natively into CSV format -> [{target_file}]")


def _export_json(target_file: str, headers: list, records: list) -> None:
    """Serialises the result set into a structured JSON tree."""
    structured_data = [dict(zip(headers, row)) for row in records]
    with open(target_file, "w", encoding="utf-8") as json_file:
        json.dump(structured_data, json_file, indent=4, ensure_ascii=False)
    print(f"Success: {len(records)} rows exported natively into JSON format -> [{target_file}]")


def _export_pdf(target_file: str, headers: list, records: list) -> None:
    """Serialises the result set into a vectorised, multi-page PDF report."""
    if not HAS_REPORTLAB:
        print("Error: The 'reportlab' dependency is missing from the active environment.")
        print("Please install it using your system shell: pip install reportlab")
        return

    try:
        doc = SimpleDocTemplate(
            target_file,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        styles = getSampleStyleSheet()

        header_style = ParagraphStyle(
            'PDFHeaderStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.whitesmoke
        )
        cell_style = ParagraphStyle(
            'PDFCellStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.black
        )

        pdf_data = []
        wrapped_headers = [Paragraph(str(h), header_style) for h in headers]
        pdf_data.append(wrapped_headers)

        for row in records:
            wrapped_row = []
            for item in row:
                val_str = str(item) if item is not None else "NULL"
                wrapped_row.append(Paragraph(val_str, cell_style))
            pdf_data.append(wrapped_row)

        table = Table(pdf_data, repeatRows=1)

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A252C')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ])

        for i in range(1, len(pdf_data)):
            if i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F9FAFB'))

        table.setStyle(table_style)

        story = [table]
        doc.build(story)
        print(f"Success: {len(records)} rows exported natively into PDF format -> [{target_file}]")

    except Exception as pdf_error:
        print(f"PDF generation pipeline failed: {pdf_error}")
