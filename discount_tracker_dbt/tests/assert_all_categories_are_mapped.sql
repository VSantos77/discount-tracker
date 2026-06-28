SELECT 
    id,
    category_name_original
FROM {{ ref('dim_merchants') }}
WHERE category_name_normalized = 'Sin categorizar'