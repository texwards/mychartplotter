import os

# 1. Determine exactly where we are
current_dir = os.getcwd()
print(f"📂 Working in: {current_dir}")

# 2. Define the path for the hidden .streamlit folder
config_folder = os.path.join(current_dir, ".streamlit")
config_file = os.path.join(config_folder, "config.toml")

# 3. Create the folder if it doesn't exist
if not os.path.exists(config_folder):
    os.makedirs(config_folder)
    print(f"✅ Created hidden folder: .streamlit")

# 4. Write the magic permission line
content = """[server]
enableStaticServing = true
"""

with open(config_file, "w") as f:
    f.write(content)

print(f"✅ Success! Config file written to: {config_file}")
print("---------------------------------------------------")
print("⚠️ YOU MUST RESTART STREAMLIT NOW FOR THIS TO WORK ⚠️")
print("   (Press Ctrl+C in your terminal, then run 'streamlit run app.py')")