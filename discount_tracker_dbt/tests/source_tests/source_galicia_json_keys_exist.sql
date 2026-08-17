
{{ assert_payload_has_keys(
    relation=source('staging','raw_discounts'),
    column_name='raw_payload',
    expected_keys=['$.source_id', '$.tipoPromocion', '$.categoria', '$.marca', '$.fechaDesde', '$.fechaHasta', '$.porcentajeAhorro', '$.descripcionAdicional', '$.legales', '$.topeReintegro', '$.minimoCompra', '$.cuotaSinInteresHasta', '$.diasAplicacion', '$.tiendaOnline', '$.tiendaFisica', '$.leyendaCompra'],
    where_clause="spider = 'galicia'"
) }}

