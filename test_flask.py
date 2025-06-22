from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/test')
def test():
    return jsonify({
        "status": "success",
        "message": "Flask test endpoint is working!",
        "data": "This is a test response"
    })

if __name__ == '__main__':
    print("Starting test Flask server on http://localhost:5005/test")
    app.run(port=5005, debug=True)
