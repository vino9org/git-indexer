import os

from . import app

os.environ["FLASK_ENV"] = "development"

if __name__ == "__main__":
    app.run(debug=True, port=8000)
