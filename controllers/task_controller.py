# controllers/task_controller.py
from base64 import b64decode

from flask import Blueprint, render_template, jsonify, request, json, url_for
import os
from pymongo import MongoClient
import cv2
import face_recognition

task_controller = Blueprint('task_controller', __name__)


def read_img(path):
    img = cv2.imread(path)
    (h, w) = img.shape[:2]
    width = 500
    ratio = width / float(w)
    height = int(h * ratio)
    return cv2.resize(img, (width, height))


@task_controller.route('/')
def index():
    return render_template('index.html')

@task_controller.route('/attendance_page')
def attendance_page():
    return render_template('attendance_page.html')


@task_controller.route('/fetch_data')
def fetch_data():
    # Retrieve names and encodings from MongoDB
    data = get_all_data()
    return jsonify({"data": data})


def get_all_data():
    # Retrieve names and encodings from MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['face_encodings']
    data = list(collection.find({}, {'_id': 0, 'ID': 1, 'name': 1, 'Program_name': 1, 'attendance_count': 1, 'workshop_list': 1}))
    return data


def listToString(s):
    # initialize an empty string
    str1 = " "

    # return string
    return (str1.join(s))


@task_controller.route('/register')
def register():
    # Get file names from the known directory
    known_dir = 'data/known'
    file_names = [file for file in os.listdir(known_dir) if os.path.isfile(os.path.join(known_dir, file))]

    # Filter out file names that are present in the MongoDB collection
    filtered_file_names = []

    for file_name in file_names:
        print(file_name)
        # Extract the string before the "." in the file name
        id_to_check = file_name.split('.')[0]

        # Check if the extracted ID is present in the MongoDB collection
        is_present = is_id_present(id_to_check)

        # If the ID is not present, add the file name to the filtered list
        if not is_present:
            filtered_file_names.append(file_name)

    # If filtered_file_names is empty, display a message and redirect to index.html
    if not filtered_file_names:
        message = "All users are already registered!"
        return jsonify({"message": message, "redirect": url_for('task_controller.index')})

    # Get input arrays from request parameters
    input_array1 = json.loads(request.args.get('inputArray1'))
    input_array2 = json.loads(request.args.get('inputArray2'))

    print(listToString(input_array1))
    print(listToString(input_array2))
    # Insert file names and encodings into MongoDB collection
    insert_file_names_and_encodings(known_dir, filtered_file_names, input_array1, input_array2)

    # Prepare the registration message
    message = "File names and encodings inserted into MongoDB!"
    # Print the received data
    print(f"File names: {file_names}")
    print(f"Input Array 1: {input_array1}")
    print(f"Input Array 2: {input_array2}")

    # Return the file names and message
    # Return the file names, input arrays, and message
    return jsonify(
        {"file_names": file_names, "input_array1": input_array1, "input_array2": input_array2, "message": message})


def insert_file_names_and_encodings(known_dir, file_names,input_array1, input_array2):
    # Insert file names and encodings into MongoDB collection
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['face_encodings']

    for i, file_name in enumerate(file_names):
        img_path = os.path.join(known_dir, file_name)
        img = read_img(img_path)
        img_enc = face_recognition.face_encodings(img)[0]

        data = {
            "ID": file_name.split('.')[0],
            "name": input_array1[i],
            "Program_name": input_array2[i],
            "encoding": img_enc.tolist(),
            "attendance_count": 0,
            "workshop_list": []
        }
        collection.insert_one(data)


@task_controller.route('/register_page')
def register_page():
    return render_template('register_page.html')


@task_controller.route('/all_registered_data')
def all_registered_data():
    # Retrieve all registered students' data from MongoDB
    data = get_all_data()
    return jsonify({"data": data})

#@task_controller.route('/get_known_files')
#def get_known_files():
#    known_dir = 'data/known'
#    file_names = [file for file in os.listdir(known_dir) if os.path.isfile(os.path.join(known_dir, file))]
#    return jsonify({"fileNames": file_names})


@task_controller.route('/get_known_files')
def get_known_files():
    known_dir = 'data/known'
    file_names = [file for file in os.listdir(known_dir) if os.path.isfile(os.path.join(known_dir, file))]

    # Filter out file names that are present in the MongoDB collection
    filtered_file_names = []

    for file_name in file_names:
        # Extract the string before the "." in the file name
        id_to_check = file_name.split('.')[0]

        # Check if the extracted ID is present in the MongoDB collection
        is_present = is_id_present(id_to_check)

        # If the ID is not present, add the file name to the filtered list
        if not is_present:
            filtered_file_names.append(file_name)

    return jsonify({"fileNames": filtered_file_names})

def is_id_present(file_name):
    # Check if the file name is present in any "ID" values in the MongoDB collection
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['face_encodings']

    query = {"ID": file_name}
    result = collection.find_one(query)
    return result is not None


@task_controller.route('/get_unknown_files')
def get_unknown_files():
    unknown_dir = 'data/unknown'
    file_names = [file for file in os.listdir(unknown_dir) if os.path.isfile(os.path.join(unknown_dir, file))]
    return jsonify({"fileNames": file_names})



@task_controller.route('/process_unknown_files')
def process_unknown_files():
    # Get encodings and names from MongoDB collection
    known_encodings, known_names = get_known_encodings()

    # Process files in the "unknown" folder
    unknown_dir = 'data/unknown'
    results = []

    for file in os.listdir(unknown_dir):
        print("Processing", file)
        img_path = os.path.join(unknown_dir, file)
        img = read_img(img_path)
        img_enc = face_recognition.face_encodings(img)[0]

        # Compare the unknown encoding with known encodings
        comparison_results = face_recognition.compare_faces(known_encodings, img_enc)

        print(f"Comparison results for {file}: {comparison_results}")

        # Find the index of the first True result (if any)
        try:
            true_index = comparison_results.index(True)
            true_name = known_names[true_index]
            print(f"True Name for {file}: {true_name}")

            # Retrieve the corresponding document from MongoDB
            client = MongoClient("mongodb://localhost:27017")
            db = client['ADT_project']
            collection = db['face_encodings']
            query = {"ID": true_name}
            user_data = collection.find_one(query)

            # Check if the selected workshop is not empty
            selected_workshop = request.args.get('selectedWorkshop')
            print(selected_workshop);
            if selected_workshop and (selected_workshop not in user_data.get("workshop_list", [])):
                print("addeddddddd");
                # Update the attendance_count field only if the workshop is not in the student's workshop_list
                attendance_count = user_data.get("attendance_count", 0) + 1
                collection.update_one(query, {"$set": {"attendance_count": attendance_count}})

        except ValueError:
            true_name = "Unknown"
            print(f"No match found for {file}")

        # Convert numpy.bool_ objects to regular booleans
        comparison_results = [bool(result) for result in comparison_results]

        results.append({"file": file, "result": comparison_results, "true_name": true_name})

    return jsonify({"results": results})


def get_known_encodings():
    # Retrieve names and encodings from MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['face_encodings']
    data = list(collection.find({}, {'_id': 0, 'ID': 1, 'encoding': 1}))

    known_encodings = [item['encoding'] for item in data]
    known_names = [item['ID'] for item in data]

    return known_encodings, known_names

@task_controller.route('/capture_photo')
def capture_photo():
    return render_template('capture_photo.html')

@task_controller.route('/save_captured_photo', methods=['POST'])
def save_captured_photo():
    try:
        # Get file name and image data from the request
        file_name = request.form.get('fileName')
        image_data_url = request.form.get('imageDataUrl')

        # Extract the base64-encoded image data
        _, encoded_data = image_data_url.split(',')

        # Convert base64 to binary
        binary_data = b64decode(encoded_data)

        # Specify the directory path to save the photo
        save_path = 'data/Unknown'

        # Ensure the directory exists
        os.makedirs(save_path, exist_ok=True)

        # Save the image as a PNG file
        file_path = os.path.join(save_path, file_name + '.png')
        with open(file_path, 'wb') as f:
            f.write(binary_data)

        message = f"Photo saved successfully at: {file_path}"
        return jsonify({"message": message})
    except Exception as e:
        error_message = f"Error saving photo: {str(e)}"
        return jsonify({"error": error_message})

@task_controller.route('/register_photo')
def register_photo():
    return render_template('register_photo.html')

@task_controller.route('/save_registered_photo', methods=['POST'])
def save_registered_photo():
        try:
            # Get file name and image data from the request
            file_name = request.form.get('fileName')
            image_data_url = request.form.get('imageDataUrl')

            # Extract the base64-encoded image data
            _, encoded_data = image_data_url.split(',')

            # Convert base64 to binary
            binary_data = b64decode(encoded_data)

            # Specify the directory path to save the registered photo
            save_path = 'data/known'

            # Ensure the directory exists
            os.makedirs(save_path, exist_ok=True)

            # Save the image as a PNG file
            file_path = os.path.join(save_path, file_name + '.png')
            with open(file_path, 'wb') as f:
                f.write(binary_data)

            message = f"Registered photo saved successfully at: {file_path}"
            return jsonify({"message": message})
        except Exception as e:
            error_message = f"Error saving registered photo: {str(e)}"
            return jsonify({"error": error_message})



@task_controller.route('/clear_registered_users')
def clear_registered_users():
    try:
        # Specify the directory path to clear registered users
        clear_path = 'data/known'

        # Remove all files in the directory
        for file_name in os.listdir(clear_path):
            file_path = os.path.join(clear_path, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Clear the MongoDB collection
        client = MongoClient("mongodb://localhost:27017")
        db = client['ADT_project']
        collection = db['face_encodings']
        collection.delete_many({})  # Clear all documents in the collection

        message = "Registered users and data cleared successfully."
        return jsonify({"message": message})
    except Exception as e:
        error_message = f"Error clearing registered users: {str(e)}"
        return jsonify({"error": error_message})

@task_controller.route('/clear_attendance_list')
def clear_attendance_list():
    try:
        # Specify the directory path to clear the attendance list
        clear_path = 'data/Unknown'

        # Remove all files in the directory
        for file_name in os.listdir(clear_path):
            file_path = os.path.join(clear_path, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        message = "Attendance list cleared successfully."
        return jsonify({"message": message})
    except Exception as e:
        error_message = f"Error clearing attendance list: {str(e)}"
        return jsonify({"error": error_message})

@task_controller.route('/register_workshop', methods=['POST'])
def register_workshop():
    try:
        # Get workshop details from the request
        workshop_name = request.form.get('workshopName')
        presenter_name = request.form.get('presenterName')

        # Save workshop details to MongoDB collection
        save_workshop_details(workshop_name, presenter_name)

        message = f"Workshop registered successfully: {workshop_name} by {presenter_name}"
        return jsonify({"message": message})
    except Exception as e:
        error_message = f"Error registering workshop: {str(e)}"
        return jsonify({"error": error_message})

def save_workshop_details(workshop_name, presenter_name):
    # Save workshop details to MongoDB collection
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['workshop_dets']

    data = {
        "workshop_name": workshop_name,
        "presenter_name": presenter_name,
        "student_list": []
    }
    collection.insert_one(data)

@task_controller.route('/get_workshop_names')
def get_workshop_names():
    # Retrieve workshop names from MongoDB collection
    client = MongoClient("mongodb://localhost:27017")
    db = client['ADT_project']
    collection = db['workshop_dets']
    data = list(collection.distinct('workshop_name'))
    return jsonify({"workshopNames": data})

@task_controller.route('/update_workshop_list', methods=['POST'])
def update_workshop_list():
    try:
        # Get data from the request
        student_id = request.form.get('id')
        workshop = request.form.get('workshop')

        print(f"Student ID: {student_id}")

        # Check if the workshop is already in the student's workshop_list
        client = MongoClient("mongodb://localhost:27017")
        db = client['ADT_project']
        face_collection = db['face_encodings']
        workshop_collection = db['workshop_dets']

        face_query = {"ID": student_id}
        student_data = face_collection.find_one(face_query)

        if workshop in student_data.get("workshop_list", []):
            message = f"Workshop {workshop} is already in student {student_id}'s workshop_list."
            return jsonify({"message": message})

        # Check if the student is already in the workshop's student_list
        workshop_query = {"workshop_name": workshop}
        workshop_data = workshop_collection.find_one(workshop_query)

        if student_id in workshop_data.get("student_list", []):
            message = f"Student {student_id} is already in workshop {workshop}'s student_list."
            return jsonify({"message": message})

        # Update the student's document in the face_encodings collection
        face_collection.update_one(face_query, {"$addToSet": {"workshop_list": workshop}})

        # Update the workshop's document in the workshop_dets collection
        workshop_collection.update_one(workshop_query, {"$addToSet": {"student_list": student_id}})

        success_message = f"Workshop {workshop} added to student {student_id}'s workshop_list."
        return jsonify({"message": success_message})
    except Exception as e:
        error_message = f"Error updating workshop list: {str(e)}"
        return jsonify({"error": error_message})

# Modify the existing route in your Flask application

#@task_controller.route('/check_file_name_or_id')
#def check_file_name_or_id():
#    try:
#        # Get the file name from the request
#        file_name = request.args.get('fileName')
#        print(file_name)

#        # Check if the ID is present in the MongoDB collection
#        is_present = is_id_present(file_name)
#        print(is_present)

#        return jsonify({"isPresent": is_present})
#    except Exception as e:
#        error_message = f"Error checking ID: {str(e)}"
#        return jsonify({"error": error_message})

#def is_id_present(file_name):
    # Extract the string before the "." in the file name
#    id_to_check = file_name.split('.')[0]
#    print(id_to_check)

    # Check if the extracted ID is present in the MongoDB collection
#    client = MongoClient("mongodb://localhost:27017")
#    db = client['ADT_project']
#    collection = db['face_encodings']

#    query = {"ID": id_to_check}
#    result = collection.find_one(query)
#    return result is not None
