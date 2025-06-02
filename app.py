from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
from datetime import datetime
import os
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = "nějaký_dlouhý_náhodný_řetězec"  # <- Tohle přidej

# Data structures
# Načtení personálu ze souboru, pokud existuje
if os.path.exists("personnel.json"):
    with open("personnel.json", "r", encoding="utf-8") as f:
        personnel = json.load(f)
else:
    personnel = []


# Cesta k dočasnému souboru
TEMP_FILE = "temp_categories.json"

SHIFTS_DATA_PERSON = "shifts_data_person.json"

SHIFTS_FILE = "shifts.json"


def load_shifts():
    if os.path.exists(SHIFTS_FILE):
        with open(SHIFTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_shifts_to_file(data):
    with open(SHIFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_temp_data(temp_data):
    with open(TEMP_FILE, "w", encoding="utf-8") as file:
        json.dump(temp_data, file, indent=4)


def load_temp_data():
    if os.path.exists(TEMP_FILE):
        with open(TEMP_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


@app.route("/")
def main_menu():
    return render_template("index.html")


@app.route("/update_category", methods=["POST"])
def update_category():
    temp_data = load_temp_data()  # Načtení dočasného souboru

    name = request.form.get("name")
    new_category = request.form.get("category")

    if name and new_category is not None:
        temp_data[name] = new_category  # Uložení dočasné hodnoty
        save_temp_data(temp_data)  # Uložení zpět do souboru

    return '', 204


@app.route("/personnel", methods=["POST"])
def update_personnel():
    global personnel

    shifts = []

    new_person = {
        "name": request.form.get("name"),
        "surname": request.form.get("surname"),
        "birth_date": request.form.get("birth_date"),
        "working": False  # Výchozí hodnota
    }
    personnel.append(new_person)

    # Přidání prázdného záznamu do shifts pro nového zaměstnance
    new_shifts = {"shifts": [{"status": "neznámý"} for _ in range(36)]}
    shifts.append(new_shifts)
    save_shifts_to_file(shifts)

    return redirect(url_for("personnel_menu"))


@app.route("/remove_personnel", methods=["POST"])
def remove_personnel():
    global personnel, shifts
    full_name = request.form.get("full_name")

    # Najdeme index zaměstnance k odebrání
    index_to_remove = None
    for index, person in enumerate(personnel):
        if f"{person['name']} {person['surname']}" == full_name:
            index_to_remove = index
            break

    if index_to_remove is not None:
        personnel.pop(index_to_remove)
        shifts.pop(index_to_remove)  # Odebereme i odpovídající směny

    return redirect(url_for("personnel_menu"))


@app.route("/personnel", methods=["GET", "POST"])
def personnel_menu():
    global personnel
    if request.method == "POST":
        # Pokud jsou odeslána zaškrtávací políčka
        working = request.form.getlist("working[]")

        # Aktualizace stavu "v práci" pro každého zaměstnance
        for person in personnel:
            full_name = f"{person['name']} {person['surname']}"
            person["working"] = full_name in working

        # Přidání nového člena personálu
        if "name" in request.form and "surname" in request.form and "birth_date" in request.form:
            name = request.form["name"]
            surname = request.form["surname"]
            birth_date = request.form["birth_date"]
            personnel.append({"name": name, "surname": surname, "birth_date": birth_date, "working": False})

    save_personnel()
    return render_template("personnel.html", personnel=personnel)



@app.route("/shifts", methods=["GET", "POST"])
def shifts_menu():
    global personnel

    shifts_data_person = session.get("shifts_data_person", {})

    update_category()

    # Pracující osoby
    working_personnel = [p for p in personnel if p.get("working", False)]
    shift_data = request.form.getlist("shift_data[]")


    if request.method == "POST":
        smeny = []
        idx = 0

        # Seřadíme podle klíčů ve správném pořadí (row_id jako číslo)
        for row_id in sorted(shifts_data_person.keys(), key=lambda x: int(x)):
            name = shifts_data_person[row_id]
            person_shifts = {"name": name, "shifts": []}
            for time_slot in range(36):
                status = shift_data[idx] if idx < len(shift_data) else ""
                person_shifts["shifts"].append({
                    "time_slot": time_slot,
                    "status": shift_data[idx]
                })
                idx += 1
            smeny.append(person_shifts)

        save_shifts_to_file(smeny)

    # Pokud neproběhl POST, načti existující směny
    else:
        smeny = load_shifts()

        if not smeny:
            smeny = []
            for person in working_personnel:
                person_shifts = {
                    "name": f"{person['name']} {person['surname']}",
                    "shifts": [{"time_slot": i, "status": ""} for i in range(36)]
                }
                smeny.append(person_shifts)

    indexed_personnel = list(enumerate(working_personnel))
    temp_data = load_temp_data()

    return render_template("shifts.html", personnel=indexed_personnel, temp_data=temp_data,
                           shifts=smeny, shifts_data_person=shifts_data_person,
                           working_personnel=working_personnel)


@app.route("/update_shift", methods=["POST"])
def update_shift():
    shifts = load_shifts()
    try:
        row = int(request.form.get("row", "0"))
        slot = int(request.form.get("slot", "0"))
        status = request.form.get("status")
    except ValueError:
        return "Neplatné hodnoty", 400

    # Pokud směny neexistují, vytvoříme prázdnou strukturu
    while len(shifts) <= row:
        shifts.append({
            "name": f"Osoba {row + 1}",
            "shifts": [{"time_slot": i, "status": ""} for i in range(36)]
        })

    # Upravíme příslušný slot
    shifts[row]["shifts"][slot]["status"] = status
    save_shifts_to_file(shifts)

    return "OK"



@app.route("/save_shifts", methods=["POST"])
def save_shifts():
    smeny = load_shifts()
    if smeny:  # Zkontrolujeme, zda existují data k uložení
        # Uložení směn do souboru
        with open(f"shifts_{datetime.now().strftime('%Y-%m-%d')}.json", "w", encoding="utf-8") as f:
            json.dump(smeny, f, ensure_ascii=False, indent=4)

        # Vymazání směn z paměti po jejich uložení
        smeny = []

        # Po uložení vymažeme dočasný soubor
        if os.path.exists(SHIFTS_FILE):
            os.remove(SHIFTS_FILE)

    return redirect(url_for("shifts_menu"))


@app.route("/history", methods=["GET", "POST"])
def history_menu():
    shifts_history = None
    error = None
    date = None

    if request.method == "POST":
        date = request.form.get("date")

        if not date:
            error = "Datum musí být zadáno."
        else:
            file_path = f"shifts_{date}.json"
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    shifts_history = json.load(f)
            else:
                error = "Soubor se směnami pro vybrané datum nebyl nalezen."


    return render_template("history.html", shifts_history=shifts_history, error=error, request=request)


@app.route("/update_working_status", methods=["POST"])
def update_working_status():
    global personnel
    data = request.get_json()
    full_name = data.get("name")
    working = data.get("working", False)

    # Najdeme odpovídajícího zaměstnance a aktualizujeme jeho stav
    for person in personnel:
        if f"{person['name']} {person['surname']}" == full_name:
            person["working"] = working
            break

    # Vracíme potvrzení
    return {"status": "success"}


def save_personnel():
    with open("personnel.json", "w", encoding="utf-8") as file:
        json.dump(personnel, file, indent=4)



@app.route("/remove", methods=["POST"])
def remove():
    global personnel, shifts

    full_name = request.form.get("person_name")
    print(full_name)

    if not full_name:
        return "Chyba: Nebylo zadáno jméno zaměstnance", 400

    # Ověření, zda zaměstnanec existuje
    person_exists = any(person for person in personnel if f"{person['name']} {person['surname']}" == full_name)

    if not person_exists:
        return f"Chyba: Zaměstnanec '{full_name}' nebyl nalezen", 400

    # Odstranění zaměstnance
    personnel = [person for person in personnel if f"{person['name']} {person['surname']}" != full_name]
    # shifts = [shift for shift in shifts if f"{shift['name']} {shift['surname']}" != full_name]

    save_personnel()
    return redirect(url_for("personnel_menu"))


@app.route("/add_personnel", methods=["POST"])
def add_personnel():
    global personnel

    name = request.form.get("name")
    surname = request.form.get("surname")
    birth_date = request.form.get("birth_date")

    # Ověření duplicity
    if any(person for person in personnel if person["name"] == name and person["surname"] == surname):
        return f"Chyba: Zaměstnanec '{name} {surname}' už existuje", 400

    new_person = {
        "name": name,
        "surname": surname,
        "birth_date": birth_date,
        "working": False
    }
    personnel.append(new_person)

    return redirect(url_for("personnel_menu"))


@app.route("/shutdown", methods=["POST"])
def shutdown():
    os._exit(0)  # tvrdé ukončení aplikace (funguje i v .exe)


def run_app():
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    run_app()

