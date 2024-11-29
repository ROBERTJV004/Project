CREATE TABLE partners (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
from flask import Flask, request, jsonify, render_template
import psycopg2
import os

# Gebruik dezelfde databaseverbinding die je eerder hebt gedefinieerd
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e


# Partner aanmeldingspagina (GET)
@app.route('/partners/register', methods=['GET'])
def partner_register_page():
    return render_template('partner_register.html')  # HTML-formulier voor partnerregistratie


# API voor partnerregistratie (POST)
@app.route('/partners/register', methods=['POST'])
def register_partner():
    try:
        # Verkrijg gegevens van het formulier
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            return jsonify({"error": "Alle velden zijn verplicht"}), 400

        # Voeg partnergegevens toe aan de database
        query = """
        INSERT INTO partners (name, email, message)
        VALUES (%s, %s, %s)
        RETURNING id;
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (name, email, message))
        partner_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Geef succesbericht terug
        return jsonify({"message": "Partner succesvol geregistreerd!", "partner_id": partner_id}), 201

    except Exception as e:
        return jsonify({"error": f"Er is een fout opgetreden: {str(e)}"}), 500


# Partnerlijst (GET)
@app.route('/partners', methods=['GET'])
def get_partners():
    try:
        # Haal alle partners op uit de database
        query = "SELECT id, name, email, message, created_at FROM partners;"
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        partners = cur.fetchall()
        cur.close()
        conn.close()

        # Formatteer de gegevens en geef terug
        partners_list = [
            {
                "id": partner[0],
                "name": partner[1],
                "email": partner[2],
                "message": partner[3],
                "created_at": partner[4]
            }
            for partner in partners
        ]

        return jsonify({"partners": partners_list}), 200

    except Exception as e:
        return jsonify({"error": f"Er is een fout opgetreden: {str(e)}"}), 500


# Partnerpagina (GET) - Bekijk details van een specifieke partner
@app.route('/partners/<int:partner_id>', methods=['GET'])
def get_partner_details(partner_id):
    try:
        # Haal partnergegevens op van de database
        query = "SELECT id, name, email, message, created_at FROM partners WHERE id = %s;"
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (partner_id,))
        partner = cur.fetchone()
        cur.close()
        conn.close()

        if partner:
            partner_details = {
                "id": partner[0],
                "name": partner[1],
                "email": partner[2],
                "message": partner[3],
                "created_at": partner[4]
            }
            return jsonify({"partner": partner_details}), 200
        else:
            return jsonify({"error": "Partner niet gevonden"}), 404

    except Exception as e:
        return jsonify({"error": f"Er is een fout opgetreden: {str(e)}"}), 500

from flask import render_template, request, jsonify

@app.route('/partners/register', methods=['GET'])
def partner_register_page():
    return render_template('partner_register.html')  # HTML-formulier voor partnerregistratie

@app.route('/partners/register', methods=['POST'])
def register_partner():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            return render_template('partner_register.html', error="Alle velden zijn verplicht")

        # Voeg partnergegevens toe aan de database
        query = """
        INSERT INTO partners (name, email, message)
        VALUES (%s, %s, %s)
        RETURNING id;
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (name, email, message))
        partner_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Geef succesbericht terug
        return render_template('partner_register.html', success="Partner succesvol geregistreerd!")

    except Exception as e:
        return render_template('partner_register.html', error=f"Er is een fout opgetreden: {str(e)}")
