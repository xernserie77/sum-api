from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_sqlalchemy import SQLAlchemy
import hashlib
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sumdb.sqlite3'

db = SQLAlchemy(app)
api = Api(app, version='1.0', title='Sum API', description='API that returns sum of a list of numbers with caching')

ns = api.namespace('sum', description='Sum operations')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_hash = db.Column(db.String(64), unique=True, nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    result = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()

sum_input = api.model('SumInput', {
    'numbers': fields.List(fields.Integer, required=True, description='List of integers')
})

sum_output = api.model('SumOutput', {
    'sum': fields.Integer(description='The sum of the list'),
    'cached': fields.Boolean(description='Whether the result was returned from cache')
})

@ns.route('/')
class SumAPI(Resource):
    @ns.expect(sum_input)
    @ns.marshal_with(sum_output)
    def post(self):
        data = request.get_json()
        numbers = data.get('numbers')

        if not isinstance(numbers, list) or not all(isinstance(n, int) for n in numbers):
            api.abort(400, 'Input must be a list of integers.')

        sorted_input = sorted(numbers)
        input_str = json.dumps(sorted_input)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()

        txn = Transaction.query.filter_by(input_hash=input_hash).first()
        if txn:
            return {'sum': txn.result, 'cached': True}

        total = sum(numbers)
        txn = Transaction(input_hash=input_hash, input_data=json.dumps(numbers), result=total)
        db.session.add(txn)
        db.session.commit()

        return {'sum': total, 'cached': False}

if __name__ == '__main__':
    app.run(debug=True)
