"""Display previously saved processing errors in English without rewriting user data."""

LEGACY_PROCESSING_ERRORS = {
    "Falta configurar GEMINI_API_KEY en el servidor. Tu archivo quedó guardado.": "GEMINI_API_KEY is not configured on the server. Your file has been saved.",
    "Se agotó temporalmente la cuota de Gemini. El archivo está guardado; reintentá más tarde.": "The Gemini quota has been temporarily exceeded. Your file is saved. Try again later.",
    "Gemini rechazó la credencial. Revisá la API key y los permisos del proyecto.": "Gemini rejected the credentials. Check the API key and project permissions.",
    "El modelo configurado no está disponible. Revisá GEMINI_MODEL.": "The configured model is unavailable. Check GEMINI_MODEL.",
    "Gemini no pudo procesar el documento. Podés reintentar más tarde.": "Gemini could not process the document. Try again later.",
    "No se pudo conectar con Gemini o se agotó el tiempo de espera. Podés reintentar.": "Unable to connect to Gemini, or the request timed out. Try again.",
    "Gemini devolvió una respuesta incompleta o inválida. No se guardó como resultado; podés reintentar.": "Gemini returned an incomplete or invalid response. No results were saved. Try again.",
    "No se detectaron preguntas en el documento.": "No questions were found in the document.",
    "Ocurrió un error al procesar el archivo. Podés reintentar.": "An error occurred while processing the file. Try again.",
    "El procesamiento fue interrumpido por la migración. Podés reintentar.": "Processing was interrupted during migration. Try again."
}
