import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

NUM_TO_WORD = [
    "", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", 
    "EIGHTEEN", "NINETEEN", "TWENTY"
]

class BookDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'toc_text'):
            self.notify('TOCEntry', (0, flowable.toc_text, self.page))

def add_footer(canvas, doc):
    """
    Add the page number to the bottom center.
    Do not show footer on title page (page 1).
    """
    page_num = canvas.getPageNumber()
    if page_num > 1:
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawCentredString(A4[0] / 2.0, 0.75 * inch, f"- {page_num} -")
        canvas.restoreState()

def clean_chapter_content(content: str) -> list:
    """
    Cleans up the chapter content string and returns a list of paragraphs.
    Removes inline duplicate chapter headings, decorations, and boldings.
    """
    lines = content.split('\n')
    text = '\n'.join(lines)
    
    # Split by double newlines to form proper paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    cleaned = []
    for p in paragraphs:
        # Strip decorative lines
        if re.match(r'^=+$', p) or re.match(r'^-+$', p):
            continue
            
        # Strip if it's repeating "Chapter X" entirely
        if re.match(r'^Chapter\s+\d+.*$', p, re.IGNORECASE) and len(p.split()) < 10:
            continue
            
        # Clean markdown
        p = p.replace('**', '').replace('*', '')
        
        # Handle scene breaks
        if p == '***' or p == '#':
            cleaned.append(p)
            continue
            
        # Remove newlines within a single paragraph so it wraps naturally
        p = p.replace('\n', ' ')
        cleaned.append(p)
    return cleaned

def generate_pdf_from_data(book: dict, chapters: list, output_path: str):
    """
    Generates a polished, professional fiction manuscript-style PDF file.
    """
    title = book.get("title", "Generated Book")

    # Setup the document with 1-inch margins
    doc = BookDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # 1. Title Page Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=36,
        leading=42,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        alignment=TA_CENTER,
        textColor=HexColor('#555555'),
        spaceAfter=12
    )

    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        alignment=TA_CENTER,
        textColor=HexColor('#555555')
    )

    # 2. Table of Contents Styles
    toc_heading_style = ParagraphStyle(
        'TOCHeadingStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=36
    )
    
    # 3. Chapter Styles
    chapter_num_style = ParagraphStyle(
        'ChapterNumberStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=4,
        textTransform='uppercase'
    )
    
    chapter_title_style = ParagraphStyle(
        'ChapterTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=36 # Spacing before body text
    )
    
    # 4. Body Text Style (Standard Fiction)
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=20,
        alignment=TA_JUSTIFY,
        spaceAfter=0, # Fiction uses indentation, not paragraph spacing
        firstLineIndent=36 # 0.5 inch indent
    )

    # First paragraph of chapter gets no indent
    body_first_style = ParagraphStyle(
        'BodyFirstStyle',
        parent=body_style,
        firstLineIndent=0
    )

    # Scene Break Style
    scene_break_style = ParagraphStyle(
        'SceneBreakStyle',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        alignment=TA_CENTER,
        spaceBefore=18,
        spaceAfter=18
    )

    story = []

    # --- TITLE PAGE ---
    # Center vertically with no extra decorations
    story.append(Spacer(1, 3.5 * inch))
    story.append(Paragraph(title, title_style))
    story.append(Paragraph("A Generated Novel", subtitle_style))
    story.append(Spacer(1, 4 * inch))
    story.append(Paragraph("Generated by BookPilot AI", footer_style))
    story.append(PageBreak())

    # --- TABLE OF CONTENTS ---
    story.append(Spacer(1, 1 * inch))
    story.append(Paragraph("Table of Contents", toc_heading_style))
    
    toc = TableOfContents()
    toc.dotsMinLevel = 0 # Force dotted leaders for level 0 entries
    toc.levelStyles = [
        ParagraphStyle(
            'TOCLevel0',
            fontName='Times-Roman',
            fontSize=12,
            leading=24,
            spaceAfter=8,
            rightIndent=18 # Push numbers correctly to the right margin
        )
    ]
    story.append(toc)
    story.append(PageBreak())

    # --- CHAPTERS ---
    for chapter in chapters:
        # Extra top spacing before chapter heading (~ 30% down the page)
        story.append(Spacer(1, 3.5 * inch))
        
        chapter_num = chapter.get("chapter_number", 0)
        raw_title = chapter.get("chapter_title", "")
        clean_title = re.sub(rf'^Chapter\s+{chapter_num}[:\s-]*', '', raw_title, flags=re.IGNORECASE).strip()
        
        chapter_word = NUM_TO_WORD[chapter_num] if 0 < chapter_num < len(NUM_TO_WORD) else str(chapter_num)

        # Chapter Number (Small uppercase)
        p_num = Paragraph(f"CHAPTER {chapter_word}", chapter_num_style)
        # Notify TOC with clean title
        p_num.toc_text = f"Chapter {chapter_num} &mdash; {clean_title}"
        story.append(p_num)
        
        # Chapter Title
        if clean_title:
            story.append(Paragraph(clean_title, chapter_title_style))
        else:
            story.append(Spacer(1, 36))
            
        # Paragraphs
        paragraphs = clean_chapter_content(chapter.get("content", ""))
        first_content = True
        
        for para_text in paragraphs:
            if para_text == '***' or para_text == '#':
                story.append(Paragraph(para_text, scene_break_style))
                first_content = True # Reset indent after scene break
            else:
                if first_content:
                    story.append(Paragraph(para_text, body_first_style))
                    first_content = False
                else:
                    story.append(Paragraph(para_text, body_style))
            
        # Force next chapter to start on a new page
        story.append(PageBreak())

    # Build PDF with Page Numbers (no running headers)
    doc.multiBuild(story, onFirstPage=add_footer, onLaterPages=add_footer)
