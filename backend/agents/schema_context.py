"""
Curated schema description for the most important AdventureWorks tables.
This is the 'v1' approach — a hand-picked subset that covers the majority
of business questions. A future milestone will replace this with dynamic
RAG-based schema retrieval over pgvector.
"""

SCHEMA_CONTEXT = """
DATABASE: AdventureWorks (PostgreSQL). A bicycle-parts wholesaler.
All table/column names are lowercase. Schemas: sales, production, person.

KEY TABLES:

sales.salesorderheader
  - salesorderid (PK), orderdate (timestamp), duedate, shipdate
  - customerid (FK -> sales.customer.customerid)
  - salespersonid (FK -> sales.salesperson.businessentityid)
  - territoryid (FK -> sales.salesterritory.territoryid)
  - subtotal, taxamt, freight, totaldue (money/numeric) -- totaldue is the full order amount
  - status (int), onlineorderflag (bool)

sales.salesorderdetail
  - salesorderid + salesorderdetailid (composite PK)
  - salesorderid (FK -> salesorderheader)
  - productid (FK -> production.product.productid)
  - orderqty (smallint), unitprice (numeric), unitpricediscount (numeric, a fraction 0-1)
  - NOTE: there is NO linetotal column. Compute per-line revenue as:
    orderqty * unitprice * (1 - unitpricediscount)

sales.customer
  - customerid (PK), personid (FK -> person.person.businessentityid)
  - storeid (FK -> sales.store.businessentityid)
  - territoryid (FK -> sales.salesterritory.territoryid)

sales.salesterritory
  - territoryid (PK), name (e.g. 'Northwest', 'Canada')
  - countryregioncode, "group" (e.g. 'North America', 'Europe')
  - salesytd, saleslastyear (numeric)

sales.salesperson
  - businessentityid (PK), territoryid (FK)
  - salesquota, bonus, commissionpct, salesytd, saleslastyear

production.product
  - productid (PK), name, productnumber
  - productsubcategoryid (FK -> production.productsubcategory)
  - standardcost, listprice (numeric)
  - color, size, productline

production.productsubcategory
  - productsubcategoryid (PK), productcategoryid (FK), name

production.productcategory
  - productcategoryid (PK), name (e.g. 'Bikes', 'Components', 'Clothing', 'Accessories')

person.person
  - businessentityid (PK), firstname, lastname, persontype

COMMON JOINS:
  - Order revenue over time: sales.salesorderheader (use orderdate, totaldue)
  - Revenue by product: salesorderdetail JOIN production.product ON productid
  - Revenue by category: product -> productsubcategory -> productcategory
  - Revenue by region: salesorderheader JOIN salesterritory ON territoryid

NOTES:
  - Data spans roughly 2022-2025 (orderdate).
  - For revenue, prefer SUM(totaldue) from salesorderheader for order-level.
  - For line/product-level revenue, compute:
    SUM(orderqty * unitprice * (1 - unitpricediscount)) from salesorderdetail.
"""
