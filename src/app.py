from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.templating import Jinja2Templates
import uvicorn, aiohttp, asyncio
from io import BytesIO, StringIO
import tensorflow as tf
import PIL
import base64
import pdb
from pathlib import Path

export_file_name = 'final_model.h5'
classes = ['Cassava Bacterial Blight (CBB)', 'Cassava Mosaic Disease (CMD)', 'Cassava Brown Streak Disease (CBSD)', 'Cassava Green Mottle (CGM)', 'Healthy']
path = Path(__file__).parent

templates = Jinja2Templates(directory='src/templates')
app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='src/static'))

async def setup_learner():
    fin_model = tf.keras.models.load_model(path/'saved'/export_file_name)
    return fin_model

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
fin_model = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()

	
async def model_predict(img_b):
    image = PIL.Image.open(img_b)
    image_numpy = np.expand_dims(np.array(image), 0) #add batch dim
    # these 2 will be the only preprocessing steps required
    
    outputs = fin_model(image_numpy, training=False).numpy()
    formatted_outputs = [f"{i*100:.2f}" for i in outputs]
    pred_probs = zip(classes, map(str, formatted_outputs))

    img_data = base64.b64encode(img_b).decode()

    result = {"probs":pred_probs, "image":img_data}
    return result
   


@app.route('/upload', methods=["POST"])
async def upload():
    img_b = await request.files['file'].read()
    result = await model_predict(img_b)

    return templates.TemplateResponse('result.html', result)
	
@app.route("/classify-url", methods=["POST"])
async def classify_url():
    url = request.form["url"]
    response = await requests.get(url)
	
    results = await model_predict(response.content)
    return templates.TemplateResponse('result.html', result)
    

@app.route("/")
def form(request):
    index_html = path/'static'/'index.html'
    return HTMLResponse(index_html.open().read())

if __name__ == "__main__":
    if "serve" in sys.argv: uvicorn.run(app = app, host="0.0.0.0", port=8080)
