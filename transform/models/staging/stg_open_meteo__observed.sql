-- Reanalysis "actual" weather. Only for the perfect-weather ablation; disabled by default.
{{ config(enabled=var('observed_weather')) }}
{{ stg_open_meteo('observed', '') }}
