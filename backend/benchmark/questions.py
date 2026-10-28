"""Benchmark questions with hand-verified gold SQL (AdventureWorks, PostgreSQL).

Revenue convention (matches agents/schema_context.py):
  - order-level questions (year, month, territory, channel): SUM(totaldue)
  - product-level questions (product, category): orderqty * unitprice * (1 - unitpricediscount)

Fields:
  id, question, gold_sql, difficulty (easy | medium | hard), tags,
  order_matters: True if the row ORDER is part of the answer (e.g. "top 5")
"""

QUESTIONS = [
    {
        "id": "q01", "difficulty": "easy", "tags": ["count"], "order_matters": False,
        "question": "How many orders were placed in total?",
        "gold_sql": "SELECT COUNT(*) AS orders FROM sales.salesorderheader",
    },
    {
        "id": "q02", "difficulty": "easy", "tags": ["revenue", "time"], "order_matters": False,
        "question": "What was total revenue by year?",
        "gold_sql": """
            SELECT EXTRACT(YEAR FROM orderdate)::int AS year,
                   ROUND(SUM(totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader
            GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "q03", "difficulty": "easy", "tags": ["revenue", "region", "join"], "order_matters": False,
        "question": "What is the total revenue for each sales territory?",
        "gold_sql": """
            SELECT t.name AS territory, ROUND(SUM(soh.totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory t ON t.territoryid = soh.territoryid
            GROUP BY t.name ORDER BY revenue DESC""",
    },
    {
        "id": "q04", "difficulty": "easy", "tags": ["count", "product", "join"], "order_matters": False,
        "question": "How many products are in each product category?",
        "gold_sql": """
            SELECT pc.name AS category, COUNT(*) AS products
            FROM production.product p
            JOIN production.productsubcategory ps ON ps.productsubcategoryid = p.productsubcategoryid
            JOIN production.productcategory pc ON pc.productcategoryid = ps.productcategoryid
            GROUP BY pc.name ORDER BY products DESC""",
    },
    {
        "id": "q05", "difficulty": "medium", "tags": ["revenue", "product", "ranking", "join"], "order_matters": True,
        "question": "What are the top 5 products by revenue?",
        "gold_sql": """
            SELECT p.name AS product,
                   ROUND(SUM(sod.orderqty * sod.unitprice * (1 - sod.unitpricediscount))::numeric, 2) AS revenue
            FROM sales.salesorderdetail sod
            JOIN production.product p ON p.productid = sod.productid
            GROUP BY p.name ORDER BY revenue DESC LIMIT 5""",
    },
    {
        "id": "q06", "difficulty": "easy", "tags": ["channel", "ratio"], "order_matters": False,
        "question": "What percentage of orders were placed online?",
        "gold_sql": """
            SELECT ROUND(100.0 * SUM(CASE WHEN onlineorderflag THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_online
            FROM sales.salesorderheader""",
    },
    {
        "id": "q07", "difficulty": "easy", "tags": ["revenue", "time", "average"], "order_matters": False,
        "question": "What was the average order value in each year?",
        "gold_sql": """
            SELECT EXTRACT(YEAR FROM orderdate)::int AS year,
                   ROUND(AVG(totaldue)::numeric, 2) AS avg_order_value
            FROM sales.salesorderheader
            GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "q08", "difficulty": "medium", "tags": ["revenue", "time", "ranking"], "order_matters": True,
        "question": "Which month had the highest total revenue?",
        "gold_sql": """
            SELECT to_char(date_trunc('month', orderdate), 'YYYY-MM') AS month,
                   ROUND(SUM(totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader
            GROUP BY 1 ORDER BY revenue DESC LIMIT 1""",
    },
    {
        "id": "q09", "difficulty": "easy", "tags": ["hr", "count"], "order_matters": False,
        "question": "How many employees are there of each gender?",
        "gold_sql": """
            SELECT gender, COUNT(*) AS employees
            FROM humanresources.employee
            GROUP BY gender ORDER BY gender""",
    },
    {
        "id": "q10", "difficulty": "medium", "tags": ["revenue", "product", "join"], "order_matters": False,
        "question": "What is the total revenue for each product category?",
        "gold_sql": """
            SELECT pc.name AS category,
                   ROUND(SUM(sod.orderqty * sod.unitprice * (1 - sod.unitpricediscount))::numeric, 2) AS revenue
            FROM sales.salesorderdetail sod
            JOIN production.product p ON p.productid = sod.productid
            JOIN production.productsubcategory ps ON ps.productsubcategoryid = p.productsubcategoryid
            JOIN production.productcategory pc ON pc.productcategoryid = ps.productcategoryid
            GROUP BY pc.name ORDER BY revenue DESC""",
    },
]

# ---------- Batch 2: medium (filters, multi-table joins, rankings) ----------
QUESTIONS += [
    {
        "id": "q11", "difficulty": "easy", "tags": ["count", "region", "join"], "order_matters": False,
        "question": "How many orders were placed in each region group (North America, Europe, Pacific)?",
        "gold_sql": """
            SELECT t."group" AS region_group, COUNT(*) AS orders
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory t ON t.territoryid = soh.territoryid
            GROUP BY t."group" ORDER BY orders DESC""",
    },
    {
        "id": "q12", "difficulty": "medium", "tags": ["revenue", "people", "ranking", "join"], "order_matters": True,
        "question": "Who are the top 5 salespeople by total sales revenue?",
        "gold_sql": """
            SELECT p.firstname || ' ' || p.lastname AS salesperson,
                   ROUND(SUM(soh.totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader soh
            JOIN person.person p ON p.businessentityid = soh.salespersonid
            GROUP BY p.businessentityid, p.firstname, p.lastname
            ORDER BY revenue DESC LIMIT 5""",
    },
    {
        "id": "q13", "difficulty": "medium", "tags": ["revenue", "product", "time", "ranking", "join"], "order_matters": True,
        "question": "Which product category had the highest revenue in 2024?",
        "gold_sql": """
            SELECT pc.name AS category,
                   ROUND(SUM(sod.orderqty * sod.unitprice * (1 - sod.unitpricediscount))::numeric, 2) AS revenue
            FROM sales.salesorderdetail sod
            JOIN sales.salesorderheader soh ON soh.salesorderid = sod.salesorderid
            JOIN production.product p ON p.productid = sod.productid
            JOIN production.productsubcategory ps ON ps.productsubcategoryid = p.productsubcategoryid
            JOIN production.productcategory pc ON pc.productcategoryid = ps.productcategoryid
            WHERE EXTRACT(YEAR FROM soh.orderdate) = 2024
            GROUP BY pc.name ORDER BY revenue DESC LIMIT 1""",
    },
    {
        "id": "q14", "difficulty": "easy", "tags": ["count", "customer", "time"], "order_matters": False,
        "question": "How many distinct customers placed at least one order in 2024?",
        "gold_sql": """
            SELECT COUNT(DISTINCT customerid) AS customers
            FROM sales.salesorderheader
            WHERE EXTRACT(YEAR FROM orderdate) = 2024""",
    },
    {
        "id": "q15", "difficulty": "medium", "tags": ["revenue", "time"], "order_matters": False,
        "question": "What was the total revenue for each month of 2024?",
        "gold_sql": """
            SELECT to_char(date_trunc('month', orderdate), 'YYYY-MM') AS month,
                   ROUND(SUM(totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader
            WHERE EXTRACT(YEAR FROM orderdate) = 2024
            GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "q16", "difficulty": "medium", "tags": ["average", "orders"], "order_matters": False,
        "question": "What is the average number of line items (order lines) per order?",
        "gold_sql": """
            SELECT ROUND(COUNT(*)::numeric / COUNT(DISTINCT salesorderid), 2) AS avg_lines_per_order
            FROM sales.salesorderdetail""",
    },
    {
        "id": "q17", "difficulty": "easy", "tags": ["revenue", "channel"], "order_matters": False,
        "question": "What is the total revenue from online orders?",
        "gold_sql": """
            SELECT ROUND(SUM(totaldue)::numeric, 2) AS online_revenue
            FROM sales.salesorderheader
            WHERE onlineorderflag""",
    },
    {
        "id": "q18", "difficulty": "medium", "tags": ["count", "region", "time", "ranking", "join"], "order_matters": True,
        "question": "Which 3 sales territories had the most orders in 2023?",
        "gold_sql": """
            SELECT t.name AS territory, COUNT(*) AS orders
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory t ON t.territoryid = soh.territoryid
            WHERE EXTRACT(YEAR FROM soh.orderdate) = 2023
            GROUP BY t.name ORDER BY orders DESC LIMIT 3""",
    },
    {
        "id": "q19", "difficulty": "medium", "tags": ["quantity", "product", "ranking", "join"], "order_matters": True,
        "question": "Which product subcategory sold the most units in total?",
        "gold_sql": """
            SELECT ps.name AS subcategory, SUM(sod.orderqty) AS units
            FROM sales.salesorderdetail sod
            JOIN production.product p ON p.productid = sod.productid
            JOIN production.productsubcategory ps ON ps.productsubcategoryid = p.productsubcategoryid
            GROUP BY ps.name ORDER BY units DESC LIMIT 1""",
    },
    {
        "id": "q20", "difficulty": "easy", "tags": ["count", "filter"], "order_matters": False,
        "question": "How many orders had a total due of more than $10,000?",
        "gold_sql": """
            SELECT COUNT(*) AS orders
            FROM sales.salesorderheader
            WHERE totaldue > 10000""",
    },
]

# ---------- Batch 3: hard (multi-step calculations, anti-joins) + traps ----------
QUESTIONS += [
    {
        "id": "q21", "difficulty": "hard", "tags": ["revenue", "time", "growth"], "order_matters": False,
        "question": "By what percentage did total revenue grow from 2023 to 2024?",
        "gold_sql": """
            SELECT ROUND((100.0 * (SUM(CASE WHEN EXTRACT(YEAR FROM orderdate) = 2024 THEN totaldue END)
                                 - SUM(CASE WHEN EXTRACT(YEAR FROM orderdate) = 2023 THEN totaldue END))
                          / SUM(CASE WHEN EXTRACT(YEAR FROM orderdate) = 2023 THEN totaldue END))::numeric, 2) AS growth_pct
            FROM sales.salesorderheader""",
    },
    {
        "id": "q22", "difficulty": "medium", "tags": ["revenue", "time", "trap_recent"], "order_matters": False,
        "question": "What was the total revenue in the most recent month of data?",
        "gold_sql": """
            SELECT ROUND(SUM(totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader
            WHERE date_trunc('month', orderdate) =
                  (SELECT date_trunc('month', MAX(orderdate)) FROM sales.salesorderheader)""",
    },
    {
        "id": "q23", "difficulty": "easy", "tags": ["revenue", "time", "trap_no_data"], "order_matters": False,
        "question": "What was the total revenue in 2019?",
        "gold_sql": """
            SELECT ROUND(SUM(totaldue)::numeric, 2) AS revenue
            FROM sales.salesorderheader
            WHERE EXTRACT(YEAR FROM orderdate) = 2019""",
    },
    {
        "id": "q24", "difficulty": "hard", "tags": ["revenue", "customer", "ranking", "join"], "order_matters": True,
        "question": "Who are the top 5 individual customers by total amount spent?",
        "gold_sql": """
            SELECT p.firstname || ' ' || p.lastname AS customer,
                   ROUND(SUM(soh.totaldue)::numeric, 2) AS total_spent
            FROM sales.salesorderheader soh
            JOIN sales.customer c ON c.customerid = soh.customerid
            JOIN person.person p ON p.businessentityid = c.personid
            WHERE c.storeid IS NULL
            GROUP BY c.customerid, p.firstname, p.lastname
            ORDER BY total_spent DESC LIMIT 5""",
    },
    {
        "id": "q25", "difficulty": "hard", "tags": ["count", "product", "anti_join"], "order_matters": False,
        "question": "How many products have never been sold?",
        "gold_sql": """
            SELECT COUNT(*) AS never_sold
            FROM production.product p
            WHERE NOT EXISTS (SELECT 1 FROM sales.salesorderdetail sod WHERE sod.productid = p.productid)""",
    },
    {
        "id": "q26", "difficulty": "medium", "tags": ["average", "time", "shipping"], "order_matters": False,
        "question": "On average, how many days does it take to ship an order after it is placed?",
        "gold_sql": """
            SELECT ROUND(AVG(shipdate::date - orderdate::date)::numeric, 2) AS avg_days_to_ship
            FROM sales.salesorderheader
            WHERE shipdate IS NOT NULL""",
    },
    {
        "id": "q27", "difficulty": "hard", "tags": ["revenue", "region", "growth", "ranking", "join"], "order_matters": True,
        "question": "Which sales territory had the largest increase in revenue (in dollars) from 2023 to 2024?",
        "gold_sql": """
            SELECT t.name AS territory,
                   ROUND((SUM(CASE WHEN EXTRACT(YEAR FROM soh.orderdate) = 2024 THEN soh.totaldue ELSE 0 END)
                        - SUM(CASE WHEN EXTRACT(YEAR FROM soh.orderdate) = 2023 THEN soh.totaldue ELSE 0 END))::numeric, 2) AS increase
            FROM sales.salesorderheader soh
            JOIN sales.salesterritory t ON t.territoryid = soh.territoryid
            GROUP BY t.name ORDER BY increase DESC LIMIT 1""",
    },
    {
        "id": "q28", "difficulty": "easy", "tags": ["hr", "count", "time"], "order_matters": False,
        "question": "How many employees were hired in each year?",
        "gold_sql": """
            SELECT EXTRACT(YEAR FROM hiredate)::int AS hire_year, COUNT(*) AS employees
            FROM humanresources.employee
            GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "q29", "difficulty": "medium", "tags": ["purchasing", "time"], "order_matters": False,
        "question": "What was the total purchasing spend (purchase orders) in each year?",
        "gold_sql": """
            SELECT EXTRACT(YEAR FROM orderdate)::int AS year, ROUND(SUM(subtotal + taxamt + freight)::numeric, 2) AS spend
            FROM purchasing.purchaseorderheader
            GROUP BY 1 ORDER BY 1""",
    },
    {
        "id": "q30", "difficulty": "medium", "tags": ["count", "time", "ranking"], "order_matters": True,
        "question": "Which month of 2024 had the fewest orders?",
        "gold_sql": """
            SELECT to_char(date_trunc('month', orderdate), 'YYYY-MM') AS month, COUNT(*) AS orders
            FROM sales.salesorderheader
            WHERE EXTRACT(YEAR FROM orderdate) = 2024
            GROUP BY 1 ORDER BY orders ASC LIMIT 1""",
    },
]
