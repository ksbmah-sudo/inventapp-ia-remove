from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rembg import remove
from PIL import Image, ImageFilter, ImageDraw
import base64
import io

# Inicializamos el servidor API
app = FastAPI(title="InventApp AI Studio API")

# Permitimos que tu React (InventApp) se pueda conectar sin bloqueos de seguridad CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción aquí pondrás el dominio de tu app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definimos cómo esperamos recibir los datos
class ProductImageRequest(BaseModel):
    image_base64: str
    theme: str # Puede ser: 'transparent', 'white', 'gray', 'gradient-blue', 'gradient-dark'
    add_shadow: bool = True

def add_drop_shadow(image: Image.Image) -> Image.Image:
    """Genera una sombra base profesional estilo 'PhotoRoom' bajo el producto"""
    # Encontrar la caja delimitadora del producto real (ignora lo transparente)
    bbox = image.getbbox()
    if not bbox:
        return image

    # Crear una imagen vacía para la sombra
    shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)

    # Calcular dónde irá la sombra (justo debajo del producto)
    left, top, right, bottom = bbox
    width = right - left
    
    # Dibujar un óvalo negro semitransparente
    shadow_box =[left + (width*0.1), bottom - 15, right - (width*0.1), bottom + 15]
    draw.ellipse(shadow_box, fill=(0, 0, 0, 150))
    
    # Difuminar la sombra para que se vea natural
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    
    # Pegar el producto original sobre la sombra
    shadow.paste(image, (0,0), image)
    return shadow

@app.post("/api/studio/process")
async def process_product_image(request: ProductImageRequest):
    try:
        # 1. Leer la imagen que manda React
        image_data = base64.b64decode(request.image_base64.split(",")[1] if "," in request.image_base64 else request.image_base64)
        input_image = Image.open(io.BytesIO(image_data)).convert("RGBA")

        # 2. IA MAGIA: Quitar el fondo con altísima precisión
        output_image = remove(input_image)

        # 3. Añadir sombra artificial si se solicita
        if request.add_shadow:
            output_image = add_drop_shadow(output_image)

        # 4. Crear el fondo de estudio
        bg_size = output_image.size
        if request.theme == 'transparent':
            final_image = output_image
        else:
            final_image = Image.new('RGBA', bg_size)
            
            if request.theme == 'white':
                bg_color = (255, 255, 255, 255)
                final_image.paste(bg_color, (0, 0, bg_size[0], bg_size[1]))
            elif request.theme == 'gray':
                bg_color = (248, 250, 252, 255)
                final_image.paste(bg_color, (0, 0, bg_size[0], bg_size[1]))
            elif request.theme == 'gradient-blue':
                # Degradado de arriba hacia abajo
                for y in range(bg_size[1]):
                    r = int(224 - (224 - 186) * (y / bg_size[1]))
                    g = int(242 - (242 - 230) * (y / bg_size[1]))
                    b = int(254 - (254 - 253) * (y / bg_size[1]))
                    draw = ImageDraw.Draw(final_image)
                    draw.line([(0, y), (bg_size[0], y)], fill=(r, g, b, 255))
            elif request.theme == 'gradient-dark':
                for y in range(bg_size[1]):
                    r = int(30 - (30 - 15) * (y / bg_size[1]))
                    g = int(41 - (41 - 23) * (y / bg_size[1]))
                    b = int(59 - (59 - 42) * (y / bg_size[1]))
                    draw = ImageDraw.Draw(final_image)
                    draw.line([(0, y), (bg_size[0], y)], fill=(r, g, b, 255))

            # Pegamos el producto (ya con su sombra) encima del fondo creado
            final_image.paste(output_image, (0, 0), output_image)

        # 5. Convertir de nuevo a Base64 para devolvérselo a React
        buffered = io.BytesIO()
        if request.theme == 'transparent':
            final_image.save(buffered, format="PNG", optimize=True)
            img_str = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
        else:
            final_image = final_image.convert("RGB")
            final_image.save(buffered, format="JPEG", quality=85)
            img_str = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()

        return {"status": "success", "processed_image": img_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))