from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rembg import remove, new_session # <-- Agregamos new_session
from PIL import Image, ImageFilter, ImageDraw
import base64
import io

app = FastAPI(title="InventApp AI Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductImageRequest(BaseModel):
    image_base64: str
    theme: str
    add_shadow: bool = True

# 🚀 MAGIA AQUÍ: Obligamos a la IA a usar la versión "Lite" para que no sature la RAM gratuita
my_session = new_session("u2netp")

def add_drop_shadow(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    if not bbox:
        return image

    shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    left, top, right, bottom = bbox
    width = right - left
    
    shadow_box =[left + (width*0.1), bottom - 15, right - (width*0.1), bottom + 15]
    draw.ellipse(shadow_box, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    shadow.paste(image, (0,0), image)
    return shadow

@app.post("/api/studio/process")
async def process_product_image(request: ProductImageRequest):
    try:
        image_data = base64.b64decode(request.image_base64.split(",")[1] if "," in request.image_base64 else request.image_base64)
        input_image = Image.open(io.BytesIO(image_data)).convert("RGBA")

        # Usamos la sesión ligera
        output_image = remove(input_image, session=my_session)

        if request.add_shadow:
            output_image = add_drop_shadow(output_image)

        bg_size = output_image.size
        if request.theme == 'transparent':
            final_image = output_image
        else:
            final_image = Image.new('RGBA', bg_size)
            if request.theme == 'white':
                final_image.paste((255, 255, 255, 255), (0, 0, bg_size[0], bg_size[1]))
            elif request.theme == 'gray':
                final_image.paste((248, 250, 252, 255), (0, 0, bg_size[0], bg_size[1]))
            elif request.theme == 'gradient-blue':
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
            final_image.paste(output_image, (0, 0), output_image)

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
