from app import create_app
from wsgiref.handlers import CGIHandler

app = create_app()

def handler(event, context):
    return CGIHandler().run(app)