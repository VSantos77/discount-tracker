TRUNCATE TABLE
	dim_issuers,
	dim_merchants,
	dim_payment_methods_raw,
	fct_discounts,
	map_discount_payment_methods,
	stg_discounts
RESTART IDENTITY CASCADE;