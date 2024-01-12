from flask import Flask, render_template
from controllers.task_controller import task_controller

app = Flask(__name__)
app.config['MONGO_URI'] = "mongodb://localhost:27017/ADT_project"

app.register_blueprint(task_controller)

if __name__ == '__main__':
    app.run(debug=True)
