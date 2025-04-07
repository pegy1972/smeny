from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Data structures
# Načtení personálu ze souboru, pokud existuje
if os.path.exists("personnel.json"):
    with open("personnel.json", "r", encoding="utf-8") as f:
        personnel = json.load(f)
else:
    personnel = []

shifts = []


@app.route("/")
def main_menu():
    return render_template("index.html")


@app.route("/personnel", methods=["POST"])
def update_personnel():
    global personnel, shifts
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

        # Uložení personálu do souboru (nepovinné)
        with open("personnel.json", "w", encoding="utf-8") as f:
            json.dump(personnel, f, ensure_ascii=False, indent=4)
    return render_template("personnel.html", personnel=personnel)



@app.route("/shifts", methods=["GET", "POST"])
def shifts_menu():
    global personnel, shifts

    # Synchronizace `shifts` s `personnel`
    while len(shifts) < len(personnel):
        new_shifts = {"shifts": [{"status": "neznámý"} for _ in range(36)]}
        shifts.append(new_shifts)

    while len(shifts) > len(personnel):
        shifts.pop()

    # Filtrujeme zaměstnance, kteří jsou označeni jako "v práci"
    working_personnel = [person for person in personnel if person.get("working", False)]

    if request.method == "POST":
        shift_data = request.form.getlist("shift_data[]")
        shifts = []

        # Pro každého "pracujícího" zaměstnance uložíme směny
        idx = 0
        for person in working_personnel:
            person_shifts = {"name": f"{person['name']} {person['surname']}", "shifts": []}
            for time_slot in range(36):  # Pro každého zaměstnance projdeme jeho sloty
                person_shifts["shifts"].append({"time_slot": time_slot, "status": shift_data[idx]})
                idx += 1
            shifts.append(person_shifts)
    # Předávání dat do šablony - přidáme indexy osob
    indexed_personnel = list(enumerate(working_personnel))
    return render_template("shifts.html", personnel=indexed_personnel, shifts=shifts)


@app.route("/save_shifts", methods=["POST"])
def save_shifts():
    global shifts
    if shifts:  # Zkontrolujeme, zda existují data k uložení
        # Uložení směn do souboru
        with open(f"shifts_{datetime.now().strftime('%Y-%m-%d')}.json", "w") as f:
            json.dump(shifts, f, ensure_ascii=False, indent=4)

        # Vymazání směn z paměti po jejich uložení
        shifts = []
    return redirect(url_for("shifts_menu"))


@app.route("/history", methods=["GET", "POST"])
def history_menu():
    if request.method == "POST":
        date = request.form["date"]
        try:
            with open(f"shifts_{date}.json", "r") as f:
                shifts_history = json.load(f)
            return render_template("history.html", shifts_history=shifts_history)
        except FileNotFoundError:
            return render_template("history.html", error="File not found.")
    return render_template("history.html")


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
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

