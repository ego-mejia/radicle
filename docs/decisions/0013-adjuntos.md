# 0013. Adjuntos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.5)

- **Almacenamiento:** `radicle/storage.py` implementa `StorageBackend` en disco (`RADICLE_STORAGE_DIR`, volumen `attachments` compartido por `app` y `worker`) y en S3 (cualquier compatible, firma v4 y rutas por path para MinIO o R2). La key es `<proyecto>/<ticket>/<adjunto>/<variante>`.
- **Tests de S3:** el spec pide MinIO con testcontainers, pero las imágenes públicas de MinIO ya no se pueden descargar. Los tests usan Adobe S3Mock, otro servidor compatible con S3, con el mismo cliente boto3.
- **Tipo de archivo:** se detecta con `filetype` por los bytes; si no es binario conocido se distingue JSON, texto UTF-8 o `application/octet-stream`. El nombre nunca decide.
- **Imágenes:** al subir se quitan los metadatos EXIF y se aplica la orientación. Se reducen al preset (`RADICLE_IMAGE_DEFAULT_RESIZE`, default `large`) en el formato original: JPEG y WebP con calidad 82, PNG optimizado. Los GIF animados no se tocan. El worker genera `thumb` (320 px) y `preview` (1280 px) en WebP; mientras no existen, se sirve el original.
- **Descarga y URLs firmadas:** `GET /attachments/{id}/content` acepta sesión, token o una firma HMAC (`expires`, `sig`) válida 5 minutos, que es la `url` que regresa la API. Con S3 redirige a una URL prefirmada de 5 minutos. Las imágenes van inline; lo demás como descarga, con `nosniff`. La clave de firma es `RADICLE_SECRET_KEY` o, si no existe, una derivada de la URL de la base.
- **Markdown:** un adjunto se referencia como `![nombre](attachment:<id>)`. La UI lo convierte en la URL de la API (con la cookie de sesión), así el texto guardado no caduca.
- **Borrar:** el registro se marca borrado (queda en el historial) y se borran los bytes y las variantes.
- **MCP:** el límite de cuerpo del transporte sube a 16 MB para que quepan los 10 MB de `upload_attachment` en base64.
- `GET /limits` dice el tamaño máximo y el preset default, para que la UI preseleccione el tamaño al pegar una imagen.
