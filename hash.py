from werkzeug.security import generate_password_hash

# Contraseña en texto plano
plain_password = "MiContrasenaSegura"

# Generar el hash
hashed_password = generate_password_hash(plain_password)

print("Hashed Password:", hashed_password)
    27 | gamueljb@gmail.com      