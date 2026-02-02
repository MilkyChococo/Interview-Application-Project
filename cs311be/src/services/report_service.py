import os
from typing import Dict, Any, List

import pdfkit


# Resolve wkhtmltopdf.exe location relative to this file
# Current file: dsc2025API/src/services/report_service.py
# Project binary exists at: dsc2025API/src/config/bin/wkhtmltopdf.exe
# So from here we need to go up one level to src, then to config/bin
WKHTMLTOPDF_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "..",  # to dsc2025API/src
    "config", "bin", "wkhtmltopdf.exe"
))

# Debug: Print the resolved path
print(f"wkhtmltopdf.exe path: {WKHTMLTOPDF_PATH}")
print(f"Path exists: {os.path.exists(WKHTMLTOPDF_PATH)}")


def _escape_html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_html(results: Dict[str, Any]) -> str:
    overall: Dict[str, Any] = results.get("overall", {})
    interactions: List[Dict[str, Any]] = results.get("interactions", [])

    overall_summary = _escape_html(overall.get("summary", ""))
    strengths = overall.get("strengths", []) or []
    improvements = overall.get("improvements", []) or []
    fitness = _escape_html(overall.get("fitness", ""))

    # Build strengths and improvements lists
    strengths_html = "".join(f"<li>{_escape_html(s)}</li>" for s in strengths)
    improvements_html = "".join(f"<li>{_escape_html(s)}</li>" for s in improvements)

    # Build per-question rows
    rows = []
    for idx, item in enumerate(interactions, start=1):
        question = _escape_html(item.get("question", ""))
        answer = _escape_html(item.get("answer", ""))
        evaluation = _escape_html(item.get("evaluation", ""))
        score = _escape_html(str(item.get("score", "")))
        improvements_item = item.get("improvements", []) or []
        improvements_text = "\n".join(f"- {impr}" for impr in improvements_item) if improvements_item else ""
        improvements_text = _escape_html(improvements_text)

        rows.append(
            f"""
            <tr>
                <td style='text-align:center'>{idx}</td>
                <td>{question}</td>
                <td>{answer}</td>
                <td>{evaluation}</td>
                <td><pre style='white-space: pre-wrap; font-family: inherit'>{improvements_text}</pre></td>
                <td style='text-align:center'>{score}</td>
            </tr>
            """
        )

    rows_html = "".join(rows)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Interview Evaluation Report</title>
  <style>
    body {{ 
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
      color: #000000; 
      line-height: 1.6;
      background-color: #fafafa;
    }}
    
    /* Main title styling */
    h1 {{ 
      font-size: 28px; 
      font-weight: 700;
      color: #000000;
      text-align: center;
      margin: 0 0 30px 0;
      padding: 20px;
      background: linear-gradient(135deg, #bdebff 0%, #46afff 100%);
      border-radius: 10px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    
    /* Section headers styling */
    h2 {{ 
      font-size: 20px; 
      font-weight: 600;
      color: #000000;
      margin: 30px 0 15px 0;
      padding: 12px 20px;
      background: linear-gradient(90deg, #bdebff, #46afff);
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
      border-left: 5px solid #2980b9;
    }}
    
    .section {{ 
      margin-bottom: 25px; 
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      border: 1px solid #e8e8e8;
    }}
    
    .muted {{ 
      color: #000000; 
      font-weight: 500;
    }}
    
    ul {{ 
      margin: 8px 0 0 20px; 
    }}
    
    li {{
      margin-bottom: 5px;
      color: #000000;
    }}
    
    /* Table styling */
    table {{ 
      width: 100%; 
      border-collapse: collapse; 
      margin-top: 15px;
      background: white;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}
    
    th {{ 
      background: linear-gradient(#bdebff 0%);
      color: #000000;
      font-weight: 600;
      text-align: left;
      padding: 15px 12px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    
    td {{ 
      border: 1px solid #e8e8e8; 
      padding: 12px; 
      vertical-align: top;
      color: #000000;
    }}
    
    tr:nth-child(even) {{
      background-color: #f8f9fa;
    }}
    
    tr:hover {{
      background-color: #e3f2fd;
      transition: background-color 0.3s ease;
    }}
    
    /* Content styling */
    p {{
      color: #000000;
      margin-bottom: 10px;
    }}
    
    strong {{
      color: #000000;
      font-weight: 600;
    }}
  </style>
  </head>
  <body>
    <h1>FINAL EVALUATION REPORT</h1>

    <div class="section">
      <h2>I. Overall Assessment</h2>
      <p>{overall_summary}</p>
      <p class="muted"><strong>Strengths:</strong></p>
      <ul>{strengths_html}</ul>
      <p class="muted" style="margin-top:8px"><strong>Areas for Improvement:</strong></p>
      <ul>{improvements_html}</ul>
      <p class="muted" style="margin-top:8px"><strong>Position Suitability:</strong> {fitness}</p>
    </div>

    <div class="section">
      <h2>II. Detailed Question-by-Question Evaluation</h2>
      <table>
        <thead>
          <tr>
            <th style='width:50px;text-align:center'>No.</th>
            <th style='width:80px'>Question</th>
            <th style='width:150px'>Candidate Answer</th>
            <th style='width:300px'>Evaluation</th>
            <th style='width:200px'>Improvements</th>
            <th style='width:50px;text-align:center'>Score</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </body>
</html>
    """
    return html


def generate_interview_report_pdf(results: Dict[str, Any]) -> bytes:
    """Render PDF bytes for final interview report from results structure.

    Expected results format:
    {
      "overall": {
        "summary": str,
        "strengths": [str, ...],
        "improvements": [str, ...],
        "fitness": str
      },
      "interactions": [
        {"question": str, "answer": str, "evaluation": str, "improvements": [str,...], "score": number},
        ...
      ]
    }
    """
    html = _build_html(results)

    config = None
    if os.path.exists(WKHTMLTOPDF_PATH):
        config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
        print(f"Using wkhtmltopdf from: {WKHTMLTOPDF_PATH}")
    else:
        print(f"wkhtmltopdf.exe not found at: {WKHTMLTOPDF_PATH}")
        print("Trying system PATH...")

    options = {
        "encoding": "UTF-8",
        "enable-local-file-access": None,
        "quiet": "",
        "page-size": "A4",
        "margin-top": "10mm",
        "margin-bottom": "12mm",
        "margin-left": "10mm",
        "margin-right": "10mm",
    }

    try:
        # If wkhtmltopdf isn't available via resolved path, allow system PATH to handle it
        # pdfkit will raise an error if not installed/available
        pdf_bytes: bytes = pdfkit.from_string(html, False, options=options, configuration=config)
        return pdf_bytes
    except Exception as e:
        print(f"PDF generation error: {e}")
        # Return a simple HTML as fallback
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Interview Report</title>
        </head>
        <body>
            <h1>Interview Report</h1>
            <p>Error generating PDF: {str(e)}</p>
            <p>Please check the server configuration and try again.</p>
        </body>
        </html>
        """
        try:
            pdf_bytes: bytes = pdfkit.from_string(fallback_html, False, options=options, configuration=config)
            return pdf_bytes
        except:
            # If even fallback fails, return empty bytes
            return b""

