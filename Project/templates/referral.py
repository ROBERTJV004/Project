@app.route('/validate_referral', methods=['POST'])
def validate_referral():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Gebruiker moet ingelogd zijn
    
    referral_code = request.form.get('referral_code').strip()
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Controleer of de code geldig is
        cur.execute("SELECT id FROM referral_codes WHERE code = %s AND used = FALSE", (referral_code,))
        code = cur.fetchone()
        if not code:
            message = "Ongeldige of reeds gebruikte code. Probeer een andere."
            return render_template('referral.html', message=message, message_class="error")

        # Controleer of gebruiker al een code heeft gebruikt
        cur.execute("SELECT id FROM users WHERE id = %s AND referral_used = TRUE", (user_id,))
        user = cur.fetchone()
        if user:
            message = "Je hebt al een referral code gebruikt."
            return render_template('referral.html', message=message, message_class="error")

        # Update referral code als gebruikt en beloon de gebruiker
        cur.execute("UPDATE referral_codes SET used = TRUE WHERE id = %s", (code[0],))
        cur.execute("UPDATE users SET referral_used = TRUE, credits = credits + 2 WHERE id = %s", (user_id,))
        conn.commit()

        message = "Gefeliciteerd! Volg nu 2 lessen zonder commissie!"
        return render_template('referral.html', message=message, message_class="reward")

    except Exception as e:
        return render_template('referral.html', message=f"Er is een fout opgetreden: {str(e)}", message_class="error")
    finally:
        cur.close()
        conn.close()
CREATE TABLE referral_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    used BOOLEAN DEFAULT FALSE
);
ALTER TABLE users ADD COLUMN referral_used BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN credits INT DEFAULT 0;

