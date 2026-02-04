/**
 * useAttributeLabels - Traduce claves de atributos a etiquetas en español.
 *
 * Los atributos se almacenan con claves en inglés (eye_color, hair_type)
 * pero deben mostrarse en español en la UI.
 */

/**
 * Mapeo de claves de atributos en inglés a etiquetas en español.
 */
const ATTRIBUTE_LABELS: Record<string, string> = {
  // Atributos físicos
  eye_color: 'Color de ojos',
  hair_color: 'Color de pelo',
  hair_type: 'Tipo de pelo',
  age: 'Edad',
  height: 'Altura',
  build: 'Complexión',
  skin: 'Piel',
  distinctive_feature: 'Rasgo distintivo',

  // Profesión y ocupación
  profession: 'Profesión',
  occupation: 'Ocupación',

  // Atributos psicológicos
  personality: 'Personalidad',
  temperament: 'Temperamento',
  motivation: 'Motivación',
  fear: 'Miedo',
  desire: 'Deseo',

  // Lugares
  location_type: 'Tipo de lugar',
  climate: 'Clima',
  atmosphere: 'Atmósfera',

  // Objetos
  material: 'Material',
  origin: 'Origen',
  function: 'Función',

  // Otros
  description: 'Descripción',
  notes: 'Notas',
}

/**
 * Obtiene la etiqueta en español para una clave de atributo.
 *
 * @param key - Clave del atributo (ej: "hair_type")
 * @returns Etiqueta en español (ej: "Tipo de pelo") o la clave formateada si no existe traducción
 */
export function getAttributeLabel(key: string): string {
  // Si existe traducción, usarla
  if (key in ATTRIBUTE_LABELS) {
    return ATTRIBUTE_LABELS[key]
  }

  // Si no existe, formatear la clave: snake_case -> Title Case
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Composable para usar en componentes Vue.
 */
export function useAttributeLabels() {
  return {
    getAttributeLabel,
    ATTRIBUTE_LABELS,
  }
}

export default useAttributeLabels
