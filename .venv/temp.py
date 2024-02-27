@app.route('/pft_situp_record', methods=['GET', 'POST'])
def pft_situp_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        situp_count = request.form.get('raw_situp')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (situp_count and act_date ): #and participant_number
            return "Sit-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
    

        # Process sit-up data
        cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_situp = cursor.fetchone()

        if existing_raw_situp:
            print("Situp data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_situp, afpsn, act_date):
                query = f"SELECT {table_name} FROM `situp_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_situp,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_situp (afpsn, act_date, raw_situp, situp) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_situp, participant_score))
                db.commit()  # Commit the changes to the database

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        return "Data submitted successfully."

    return render_template('pft_situp.html')


######

@app.route('/pft_pushup_record', methods=['GET', 'POST'])
def pft_pushup_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_pushup = request.form.get('raw_pushup')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (raw_pushup and act_date ): #and participant_number
            return "Push-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
        
        cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_pushup = cursor.fetchone()

        if existing_raw_pushup:
            print("Pushup data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_pushup, afpsn, act_date):
                query = f"SELECT {table_name} FROM `pushup_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_pushup,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_pushup (afpsn, act_date, raw_pushup, pushup) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_pushup, participant_score))
                db.commit()  # Commit the changes to the database

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, raw_pushup, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        return "Data submitted successfully."

    return render_template('pft_pushup.html')


######