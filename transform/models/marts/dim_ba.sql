select
    r.ba_code,
    r.name,
    r.timezone,
    r.n_cities,
    sum(c.population) as population_covered
from {{ ref('regions') }} as r
join {{ ref('cities') }} as c using (ba_code)
group by all
