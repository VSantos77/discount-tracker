with

bbva     as (select * from {{ ref('stg_bbva') }}),
galicia  as (select * from {{ ref('stg_galicia') }}),
naranjax as (select * from {{ ref('stg_naranjax') }})

select * from bbva
union all
select * from galicia
union all
select * from naranjax
