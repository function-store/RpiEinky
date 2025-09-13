#!/usr/bin/env python3
"""
Setup script for admin password hash
"""
import hashlib
import getpass
import os
import secrets
import string

def generate_password_hash(password):
    """Generate SHA256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_api_key(length=32):
    """Generate a secure random API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    print("E-ink Display Manager - Admin Password Setup")
    print("=" * 50)

    # Get password from user
    while True:
        password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm admin password: ")

        if password != confirm:
            print("❌ Passwords don't match. Please try again.")
            continue

        if len(password) < 6:
            print("❌ Password must be at least 6 characters long.")
            continue

        break

    # Generate hash and API key
    password_hash = generate_password_hash(password)
    api_key = generate_api_key()

    print("\n✅ Password hash generated successfully!")
    print("✅ API key generated for TouchDesigner!")
    print("\nTo use these credentials, set the environment variables:")
    print(f"export ADMIN_PASSWORD_HASH='{password_hash}'")
    print(f"export API_KEY='{api_key}'")

    # Option to create .env file
    create_env = input("\nCreate .env file with this hash? (y/n): ").lower().strip()
    if create_env == 'y':
        env_content = f"""# E-ink Display Manager Environment Variables
ADMIN_PASSWORD_HASH={password_hash}
API_KEY={api_key}
FLASK_SECRET_KEY={os.urandom(32).hex()}
"""

        with open('.env', 'w') as f:
            f.write(env_content)

        print("✅ Created .env file")
        print("⚠️  Make sure to add .env to your .gitignore file!")

        print(f"\n🎨 TouchDesigner WebClient Configuration:")
        print(f"   Authentication Type: None")
        print(f"   Add Custom Header:")
        print(f"   Header Name: X-API-Key")
        print(f"   Header Value: {api_key}")
        print(f"   \n   OR use Authorization header:")
        print(f"   Header Name: Authorization")
        print(f"   Header Value: {api_key}")

        # Check if .gitignore exists and add .env if needed
        gitignore_path = '.gitignore'
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                content = f.read()

            if '.env' not in content:
                with open(gitignore_path, 'a') as f:
                    f.write('\n# Environment variables\n.env\n')
                print("✅ Added .env to .gitignore")
        else:
            with open(gitignore_path, 'w') as f:
                f.write('# Environment variables\n.env\n')
            print("✅ Created .gitignore with .env entry")

if __name__ == '__main__':
    main()
