// Umbrales por defecto (deben coincidir con app/config.py del backend / firmware).
// El backend no expone estos valores por API, así que se replican aquí como referencia visual.
export const THRESHOLDS = {
  TEMP_MIN: 37.0,
  TEMP_MAX: 38.0,
  HUM_MIN: 50.0,
  HUM_MAX: 65.0,
};

export const MAX_CHART_POINTS = 40;
