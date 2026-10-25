import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, XPreformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_perfect_pyspark_pdf():
    # 1. Path to save the PDF file in the user's Documents directory 
    documents_dir = os.path.expanduser("~/Documents")
    pdf_file_path = os.path.join(documents_dir, "PySpark_Window_Functions_Fixed.pdf")

    doc = SimpleDocTemplate(
        pdf_file_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Title style for the document
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    # Style for XPreformatted (preserves exact \n, spaces, and indents)
    code_pre_style = ParagraphStyle(
        'Code_Preformatted',
        fontName='Courier',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#F8FAFC'),
        backColor=colors.HexColor('#0F172A'),
        spaceBefore=4,
        spaceAfter=8,
        leftIndent=4,
        rightIndent=4,
        borderPadding=8
    )

    # Style for df.show() results
    output_pre_style = ParagraphStyle(
        'Output_Preformatted',
        fontName='Courier',
        fontSize=7.0,
        leading=9.5,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F1F5F9'),
        spaceBefore=4,
        spaceAfter=8,
        leftIndent=4,
        rightIndent=4,
        borderPadding=6
    )

    story = []

    # Title
    story.append(Paragraph("PySpark Window Functions Guide", title_style))
    story.append(Paragraph("Повний довідник із точним збереженням форматування коду Python та вихідних таблиць.", body_style))

    # --- СЕКЦІЯ 1: SETUP ---
    story.append(Paragraph("1. Base Dataset Setup", h2_style))
    story.append(Paragraph("Ініціалізація сесії Spark та підготовка датасету:", body_style))

    setup_code = """from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark = SparkSession.builder \\
    .appName("SparkWindowDeepDive") \\
    .getOrCreate()

data = [
    ("Sales", "Alice", 5000, "2026-01-01"),
    ("Sales", "Bob", 5000, "2026-01-02"),
    ("Sales", "Charlie", 4000, "2026-01-03"),
    ("Sales", "David", 3000, "2026-01-04"),
    ("IT", "Eva", 8000, "2026-01-01"),
    ("IT", "Frank", 7000, "2026-01-02"),
    ("IT", "Grace", 7000, "2026-01-03"),
    ("IT", "Hank", 6000, "2026-01-04")
]

df = spark.createDataFrame(data, ["department", "employee", "amount", "date"])"""

    story.append(XPreformatted(setup_code, code_pre_style))

    # --- Section 2: RANKING FUNCTIONS ---
    story.append(Paragraph("2. Ranking Functions", h2_style))
    story.append(Paragraph("Обчислення функцій row_number, rank, dense_rank, percent_rank та ntile:", body_style))

    ranking_code = """# Define Window: Partition by department, sort by amount DESC
w_rank = Window.partitionBy("department").orderBy(F.col("amount").desc())

result_rank = df \\
    .withColumn("row_number", F.row_number().over(w_rank)) \\
    .withColumn("rank", F.rank().over(w_rank)) \\
    .withColumn("dense_rank", F.dense_rank().over(w_rank)) \\
    .withColumn("percent_rank", F.round(F.percent_rank().over(w_rank), 2)) \\
    .withColumn("ntile_2", F.ntile(2).over(w_rank))

result_rank.show()"""

    story.append(XPreformatted(ranking_code, code_pre_style))

    ranking_output = """+----------+--------+------+----------+----------+----+----------+------------+-------+
|department|employee|amount|      date|row_number|rank|dense_rank|percent_rank|ntile_2|
+----------+--------+------+----------+----------+----+----------+------------+-------+
|        IT|     Eva|  8000|2026-01-01|         1|   1|         1|         0.0|      1|
|        IT|   Frank|  7000|2026-01-02|         2|   2|         2|        0.33|      1|
|        IT|   Grace|  7000|2026-01-03|         3|   2|         2|        0.33|      2|
|        IT|    Hank|  6000|2026-01-04|         4|   4|         3|         1.0|      2|
|     Sales|   Alice|  5000|2026-01-01|         1|   1|         1|         0.0|      1|
|     Sales|     Bob|  5000|2026-01-02|         2|   1|         1|         0.0|      1|
|     Sales| Charlie|  4000|2026-01-03|         3|   3|         2|        0.67|      2|
|     Sales|   David|  3000|2026-01-04|         4|   4|         3|         1.0|      2|
+----------+--------+------+----------+----------+----+----------+------------+-------+"""

    story.append(XPreformatted(ranking_output, output_pre_style))

    # --- Section    3: ANALYTIC FUNCTIONS ---
    story.append(Paragraph("3. Analytic & Value Functions (lag / lead)", h2_style))
    story.append(Paragraph("Отримання значень із попередніх та наступних рядків:", body_style))

    analytic_code = """w_time = Window.partitionBy("department").orderBy("date")

result_analytic = df \\
    .withColumn("prev_amt", F.lag("amount", 1, 0).over(w_time)) \\
    .withColumn("next_amt", F.lead("amount", 1, 0).over(w_time)) \\
    .withColumn("diff", F.col("amount") - F.col("prev_amt"))

result_analytic.show()"""

    story.append(XPreformatted(analytic_code, code_pre_style))

    analytic_output = """+----------+--------+------+----------+--------+--------+-----+
|department|employee|amount|      date|prev_amt|next_amt| diff|
+----------+--------+------+----------+--------+--------+-----+
|        IT|     Eva|  8000|2026-01-01|       0|    7000| 8000|
|        IT|   Frank|  7000|2026-01-02|    8000|    7000|-1000|
|        IT|   Grace|  7000|2026-01-03|    7000|    6000|    0|
|        IT|    Hank|  6000|2026-01-04|    7000|       0|-1000|
|     Sales|   Alice|  5000|2026-01-01|       0|    5000| 5000|
|     Sales|     Bob|  5000|2026-01-02|    5000|    4000|    0|
|     Sales| Charlie|  4000|2026-01-03|    5000|    3000|-1000|
|     Sales|   David|  3000|2026-01-04|    4000|       0|-1000|
+----------+--------+------+----------+--------+--------+-----+"""

    story.append(XPreformatted(analytic_output, output_pre_style))

    # --- СЕКЦІЯ 4: AGGREGATE WINDOW FUNCTIONS ---
    story.append(Paragraph("4. Aggregate Window Functions", h2_style))
    story.append(Paragraph("Кумулятивна сума (running total) та ковзне середнє (moving average):", body_style))

    agg_code = """w_cum = Window.partitionBy("department").orderBy("date") \\
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

w_moving = Window.partitionBy("department").orderBy("date") \\
    .rowsBetween(-1, 1)

result_agg = df \\
    .withColumn("running_total", F.sum("amount").over(w_cum)) \\
    .withColumn("moving_avg_3r", F.round(F.avg("amount").over(w_moving), 2)) \\
    .withColumn("running_max", F.max("amount").over(w_cum))

result_agg.show()"""

    story.append(XPreformatted(agg_code, code_pre_style))

    agg_output = """+----------+--------+------+----------+-------------+------------+-----------+
|department|employee|amount|      date|running_total|moving_avg_3r|running_max|
+----------+--------+------+----------+-------------+------------+-----------+
|        IT|     Eva|  8000|2026-01-01|         8000|      7500.0|       8000|
|        IT|   Frank|  7000|2026-01-02|        15000|     7333.33|       8000|
|        IT|   Grace|  7000|2026-01-03|        22000|     6666.67|       8000|
|        IT|    Hank|  6000|2026-01-04|        28000|      6500.0|       8000|
|     Sales|   Alice|  5000|2026-01-01|         5000|      5000.0|       5000|
|     Sales|     Bob|  5000|2026-01-02|        10000|     4666.67|       5000|
|     Sales| Charlie|  4000|2026-01-03|        14000|      4000.0|       5000|
|     Sales|   David|  3000|2026-01-04|        17000|      3500.0|       5000|
+----------+--------+------+----------+-------------+------------+-----------+"""

    story.append(XPreformatted(agg_output, output_pre_style))

    # Create document
    doc.build(story)
    print(f"✅ Файл успішно згенеровано з правильним форматуванням:\n{pdf_file_path}")

if __name__ == "__main__":
    create_perfect_pyspark_pdf()