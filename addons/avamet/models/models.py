# -*- coding: utf-8 -*-

import json
from datetime import datetime, time, timedelta, timezone
from html import escape

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


REQUIRED_FIELDS = (
    "live_updated",
    "live_temp",
    "live_humidity",
    "live_pressure",
    "live_wind_kmh",
    "live_rain_mm",
)

NUMERIC_FIELDS = (
    "live_temp",
    "live_temp_min",
    "live_temp_max",
    "live_humidity",
    "live_pressure",
    "live_wind_kmh",
    "live_gust_kmh",
    "live_rain_mm",
    "live_rain_1h_mm",
    "temp_points_7d",
    "temp_last_7d",
    "temp_min_7d",
    "temp_max_7d",
    "temp_mean_7d",
    "humidity_points_7d",
    "humidity_last_7d",
    "humidity_min_7d",
    "humidity_max_7d",
    "humidity_mean_7d",
    "wind_points_7d",
    "wind_last_7d",
    "wind_min_7d",
    "wind_max_7d",
    "wind_mean_7d",
    "pressure_points_7d",
    "pressure_last_7d",
    "pressure_min_7d",
    "pressure_max_7d",
    "pressure_mean_7d",
    "last_wind_dir_deg",
    "last_rain_cumulative_mm",
    "pressure_change_3h",
    "month_days",
    "month_temp_min",
    "month_temp_mean",
    "month_temp_max",
    "month_humidity_mean",
    "month_pressure_mean",
    "month_wind_mean",
    "month_gust_max",
    "month_rain_total",
    "month_rainy_days",
    "day_temp_min",
    "day_temp_mean",
    "day_temp_max",
    "day_hum_min",
    "day_hum_mean",
    "day_hum_max",
    "day_pres_min",
    "day_pres_mean",
    "day_pres_max",
    "day_wind_mean",
    "day_gust_max",
    "day_rain_mm",
    "day_index_n",
    "day_index_p0",
    "forecast_2d_temp_min_c",
    "forecast_2d_temp_mean_c",
    "forecast_2d_temp_max_c",
    "forecast_2d_precip_mm",
    "forecast_2d_humidity_mean_pct",
    "forecast_2d_wind_mean_kmh",
    "forecast_2d_gust_max_kmh",
    "forecast_2d_pressure_mean_hpa",
    "forecast_2d_cloud_mean_pct",
)


class AvametReading(models.Model):
    _name = "avamet.reading"
    _description = "Registre meteorològic AVAMET"
    _order = "live_updated desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Registre", compute="_compute_name", store=True)
    live_updated = fields.Datetime(string="Data i hora", required=True, index=True)
    image_1 = fields.Image(string="Imatge de càmera 1", max_width=1920, max_height=1920)
    image_2 = fields.Image(string="Imatge de càmera 2", max_width=1920, max_height=1920)
    webcam1_file = fields.Char(string="Fitxer original càmera 1")
    webcam2_file = fields.Char(string="Fitxer original càmera 2")

    live_temp = fields.Float(string="Temperatura actual (°C)", required=True)
    live_temp_min = fields.Float(string="Temperatura mínima (°C)")
    live_temp_max = fields.Float(string="Temperatura màxima (°C)")
    live_humidity = fields.Float(string="Humitat actual (%)", required=True)
    live_pressure = fields.Float(string="Pressió actual (hPa)", required=True)
    live_wind_kmh = fields.Float(string="Vent actual (km/h)", required=True)
    live_wind_dir = fields.Char(string="Direcció del vent")
    live_gust_kmh = fields.Float(string="Ratxa actual (km/h)")
    live_rain_mm = fields.Float(string="Pluja acumulada (mm)", required=True)
    live_rain_1h_mm = fields.Float(string="Pluja última hora (mm)")

    series_start_utc = fields.Datetime(string="Inici de sèrie (UTC)")
    series_end_utc = fields.Datetime(string="Final de sèrie (UTC)")
    temp_points_7d = fields.Integer(string="Mostres de temperatura (7 dies)")
    temp_last_7d = fields.Float(string="Última temperatura (7 dies)")
    temp_min_7d = fields.Float(string="Temperatura mínima (7 dies)")
    temp_max_7d = fields.Float(string="Temperatura màxima (7 dies)")
    temp_mean_7d = fields.Float(string="Temperatura mitjana (7 dies)")
    humidity_points_7d = fields.Integer(string="Mostres d'humitat (7 dies)")
    humidity_last_7d = fields.Float(string="Última humitat (7 dies)")
    humidity_min_7d = fields.Float(string="Humitat mínima (7 dies)")
    humidity_max_7d = fields.Float(string="Humitat màxima (7 dies)")
    humidity_mean_7d = fields.Float(string="Humitat mitjana (7 dies)")
    wind_points_7d = fields.Integer(string="Mostres de vent (7 dies)")
    wind_last_7d = fields.Float(string="Últim vent (7 dies)")
    wind_min_7d = fields.Float(string="Vent mínim (7 dies)")
    wind_max_7d = fields.Float(string="Vent màxim (7 dies)")
    wind_mean_7d = fields.Float(string="Vent mitjà (7 dies)")
    pressure_points_7d = fields.Integer(string="Mostres de pressió (7 dies)")
    pressure_last_7d = fields.Float(string="Última pressió (7 dies)")
    pressure_min_7d = fields.Float(string="Pressió mínima (7 dies)")
    pressure_max_7d = fields.Float(string="Pressió màxima (7 dies)")
    pressure_mean_7d = fields.Float(string="Pressió mitjana (7 dies)")
    last_wind_dir_deg = fields.Float(string="Direcció del vent (graus)")
    last_rain_cumulative_mm = fields.Float(string="Pluja acumulada (mm)")
    pressure_change_3h = fields.Float(string="Canvi de pressió (3 h)")

    month = fields.Char(string="Mes de resum")
    month_days = fields.Integer(string="Dies del mes")
    month_temp_min = fields.Float(string="Temperatura mínima mensual")
    month_temp_mean = fields.Float(string="Temperatura mitjana mensual")
    month_temp_max = fields.Float(string="Temperatura màxima mensual")
    month_humidity_mean = fields.Float(string="Humitat mitjana mensual")
    month_pressure_mean = fields.Float(string="Pressió mitjana mensual")
    month_wind_mean = fields.Float(string="Vent mitjà mensual")
    month_gust_max = fields.Float(string="Ratxa màxima mensual")
    month_rain_total = fields.Float(string="Pluja mensual total")
    month_rainy_days = fields.Integer(string="Dies de pluja mensual")

    day = fields.Char(string="Dia del resum")
    day_temp_min = fields.Float(string="Temperatura mínima diària")
    day_temp_mean = fields.Float(string="Temperatura mitjana diària")
    day_temp_max = fields.Float(string="Temperatura màxima diària")
    day_hum_min = fields.Float(string="Humitat mínima diària")
    day_hum_mean = fields.Float(string="Humitat mitjana diària")
    day_hum_max = fields.Float(string="Humitat màxima diària")
    day_pres_min = fields.Float(string="Pressió mínima diària")
    day_pres_mean = fields.Float(string="Pressió mitjana diària")
    day_pres_max = fields.Float(string="Pressió màxima diària")
    day_wind_dir = fields.Char(string="Direcció mitjana diària")
    day_wind_mean = fields.Float(string="Vent mitjà diari")
    day_gust_max = fields.Float(string="Ratxa màxima diària")
    day_rain_mm = fields.Float(string="Pluja diària")
    day_index_n = fields.Float(string="Índex N diari")
    day_index_p0 = fields.Float(string="Índex P0 diari")

    forecast_2d_date = fields.Date(string="Data de previsió")
    forecast_2d_temp_min_c = fields.Float(string="Previsió: temperatura mínima")
    forecast_2d_temp_mean_c = fields.Float(string="Previsió: temperatura mitjana")
    forecast_2d_temp_max_c = fields.Float(string="Previsió: temperatura màxima")
    forecast_2d_precip_mm = fields.Float(string="Previsió: precipitació")
    forecast_2d_humidity_mean_pct = fields.Float(string="Previsió: humitat mitjana")
    forecast_2d_wind_mean_kmh = fields.Float(string="Previsió: vent mitjà")
    forecast_2d_gust_max_kmh = fields.Float(string="Previsió: ratxa màxima")
    forecast_2d_pressure_mean_hpa = fields.Float(string="Previsió: pressió mitjana")
    forecast_2d_cloud_mean_pct = fields.Float(string="Previsió: nuvolositat")

    @api.depends("live_updated")
    def _compute_name(self):
        for record in self:
            record.name = fields.Datetime.to_string(record.live_updated) if record.live_updated else "Nou registre"

    @api.model
    def default_get(self, field_names):
        defaults = super().default_get(field_names)
        latest = self.search([], order="live_updated desc, id desc", limit=1)
        if latest:
            excluded = {
                "id",
                "name",
                "live_updated",
                "image_1",
                "image_2",
                "webcam1_file",
                "webcam2_file",
            }
            for field_name in field_names:
                field = self._fields.get(field_name)
                if (
                    field
                    and field_name not in excluded
                    and field_name not in defaults
                    and field.type not in ("binary", "one2many", "many2many", "many2one")
                ):
                    defaults[field_name] = latest[field_name]
        if "live_updated" in field_names and "live_updated" not in defaults:
            defaults["live_updated"] = fields.Datetime.now()
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_daily_summaries()
        return records

    def write(self, vals):
        old_days = self._get_record_days()
        result = super().write(vals)
        self._sync_daily_summaries(old_days | self._get_record_days())
        return result

    def unlink(self):
        days = self._get_record_days()
        result = super().unlink()
        self._sync_daily_summaries(days)
        return result

    @api.constrains("live_updated", *NUMERIC_FIELDS)
    def _check_required_fields_and_numeric_change(self):
        if self.env.context.get("install_mode"):
            return

        limit = float(
            self.env["ir.config_parameter"].sudo().get_param("avamet.change_limit_percent", "100")
        )
        for record in self:
            missing = [
                self._fields[field_name].string
                for field_name in REQUIRED_FIELDS
                if record[field_name] is False
            ]
            if missing:
                raise ValidationError(
                    "Cal completar els camps obligatoris: %s." % ", ".join(missing)
                )
            if not record.live_updated:
                continue

            previous = self.search(
                [
                    ("id", "!=", record.id),
                    ("live_updated", "<=", record.live_updated),
                ],
                order="live_updated desc, id desc",
                limit=1,
            )
            following = self.search(
                [
                    ("id", "!=", record.id),
                    ("live_updated", ">=", record.live_updated),
                ],
                order="live_updated asc, id asc",
                limit=1,
            )
            candidates = (previous | following).filtered(lambda item: item.id != record.id)
            if not candidates:
                continue
            nearest = min(
                candidates,
                key=lambda item: abs((item.live_updated - record.live_updated).total_seconds()),
            )

            for field_name in NUMERIC_FIELDS:
                old_value = nearest[field_name]
                new_value = record[field_name]
                if old_value is False or new_value is False or old_value == new_value:
                    continue
                percent_change = abs(new_value - old_value) / max(abs(old_value), 1.0) * 100
                if percent_change > limit:
                    label = self._fields[field_name].string
                    raise ValidationError(
                        "%s canvia %.1f%% respecte al registre més proper "
                        "(límit configurat: %.1f%%)." % (label, percent_change, limit)
                    )

    def _get_record_days(self):
        return {
            fields.Datetime.to_datetime(record.live_updated).date()
            for record in self
            if record.live_updated
        }

    def _sync_daily_summaries(self, days=None):
        days = set(days or self._get_record_days())
        if not days:
            return

        Summary = self.env["avamet.daily.summary"].sudo()
        Reading = self.sudo()
        for summary_day in days:
            start = datetime.combine(summary_day, time.min)
            end = start + timedelta(days=1)
            readings = Reading.search(
                [
                    ("live_updated", ">=", fields.Datetime.to_string(start)),
                    ("live_updated", "<", fields.Datetime.to_string(end)),
                ],
                order="live_updated asc, id asc",
            )
            summary = Summary.search([("date", "=", summary_day)], limit=1)
            if not readings:
                if summary:
                    summary.unlink()
                continue

            summary_values = {
                "date": summary_day,
                "reading_count": len(readings),
                "summary_html": readings._make_daily_summary_html(),
            }
            if summary:
                summary.write(summary_values)
            else:
                Summary.create(summary_values)

    def _make_daily_summary_html(self):
        if not self:
            return "<p>No hi ha lectures per a aquesta data.</p>"

        metrics = (
            ("Temperatura", "live_temp", "°C"),
            ("Humitat", "live_humidity", "%"),
            ("Pressió", "live_pressure", "hPa"),
        )
        rows = []
        for label, field_name, unit in metrics:
            values = [record[field_name] for record in self if record[field_name] is not False]
            if values:
                details = " / ".join(
                    escape("%.2f" % value)
                    for value in (min(values), sum(values) / len(values), max(values))
                )
                rows.append(
                    "<li><strong>%s:</strong> %s %s "
                    "(mínim / mitjana / màxim)</li>"
                    % (escape(label), details, escape(unit))
                )

        wind_values = [record.live_wind_kmh for record in self if record.live_wind_kmh is not False]
        gust_values = [record.live_gust_kmh for record in self if record.live_gust_kmh is not False]
        rain_values = [record.live_rain_mm for record in self if record.live_rain_mm is not False]
        extras = (
            ("Vent mitjà", sum(wind_values) / len(wind_values) if wind_values else False, "km/h"),
            ("Ratxa màxima", max(gust_values) if gust_values else False, "km/h"),
            ("Pluja acumulada", rain_values[-1] if rain_values else False, "mm"),
        )
        for label, value, unit in extras:
            if value is not False:
                rows.append(
                    "<li><strong>%s:</strong> %s %s</li>"
                    % (escape(label), escape("%.2f" % value), escape(unit))
                )
        return "<ul>%s</ul>" % "".join(rows)


class AvametDailySummary(models.Model):
    _name = "avamet.daily.summary"
    _description = "Resum meteorològic diari AVAMET"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(string="Data", required=True, index=True)
    reading_count = fields.Integer(string="Nombre de registres", readonly=True)
    summary_html = fields.Html(string="Resum diari", readonly=True, sanitize=True)

    _sql_constraints = [
        ("avamet_daily_summary_date_unique", "unique(date)", "Ja existeix un resum per a aquesta data."),
    ]

    def action_view_readings(self):
        self.ensure_one()
        start = datetime.combine(self.date, time.min)
        end = start + timedelta(days=1)
        return {
            "type": "ir.actions.act_window",
            "name": "Registres del %s" % self.date,
            "res_model": "avamet.reading",
            "view_mode": "list,form",
            "domain": [
                ("live_updated", ">=", fields.Datetime.to_string(start)),
                ("live_updated", "<", fields.Datetime.to_string(end)),
            ],
        }


class AvametJsonImport(models.TransientModel):
    _name = "avamet.json.import"
    _description = "Importació d'un registre meteorològic JSON"

    json_payload = fields.Text(string="Objecte JSON", required=True)

    def action_import_record(self):
        self.ensure_one()
        try:
            values = json.loads(self.json_payload)
        except json.JSONDecodeError as error:
            raise UserError("El contingut no és un JSON vàlid: %s" % error) from error
        if not isinstance(values, dict):
            raise UserError("El JSON ha de ser un únic objecte, no una llista.")

        Reading = self.env["avamet.reading"]
        unknown = set(values) - set(Reading._fields)
        if unknown:
            raise UserError("Camps desconeguts: %s." % ", ".join(sorted(unknown)))

        missing = [field_name for field_name in REQUIRED_FIELDS if values.get(field_name) in (None, "")]
        if missing:
            labels = [Reading._fields[name].string for name in missing]
            raise UserError("Falten els camps obligatoris: %s." % ", ".join(labels))

        for field_name in ("live_updated", "series_start_utc", "series_end_utc"):
            value = values.get(field_name)
            if value:
                values[field_name] = self._normalize_datetime(value)
        if values.get("forecast_2d_date"):
            values["forecast_2d_date"] = fields.Date.to_string(
                fields.Date.to_date(values["forecast_2d_date"])
            )

        reading = Reading.create(values)
        return reading.get_formview_action()

    @staticmethod
    def _normalize_datetime(value):
        if not isinstance(value, str):
            raise UserError("Les dates i hores del JSON han d'estar en format de text.")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise UserError("Data o hora no vàlida: %s." % value) from error
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return fields.Datetime.to_string(parsed)


class AvametResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    avamet_change_limit_percent = fields.Float(
        string="Canvi numèric màxim (%)",
        default=100.0,
        config_parameter="avamet.change_limit_percent",
    )

    @api.constrains("avamet_change_limit_percent")
    def _check_avamet_change_limit(self):
        for settings in self:
            if settings.avamet_change_limit_percent < 0:
                raise ValidationError("El límit de canvi no pot ser negatiu.")
