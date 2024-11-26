from rasa_sdk.events import SlotSet
import psycopg2
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import smtplib
from email.mime.text import MIMEText
import os
from email.mime.multipart import MIMEMultipart
from psycopg2 import sql
from rasa_sdk.events import SlotSet
from langdetect import detect, LangDetectException

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid

from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

class ActionQueryDatabase(Action):
    def name(self) -> Text:
        return "action_query_database"

    def run(self, dispatcher, tracker, domain):
        # Retrieve database configuration
        db_host = os.getenv("DATABASE_HOST")
        db_user = os.getenv("DATABASE_USER")
        db_password = os.getenv("DATABASE_PASSWORD")
        db_name = os.getenv("DATABASE_NAME")
        db_port = os.getenv("DATABASE_PORT")

        try:
            # Connect to the database
            connection = psycopg2.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                port=db_port
            )
            cursor = connection.cursor()
            # Example query
            cursor.execute("SELECT * FROM users LIMIT 1;")
            result = cursor.fetchone()
            dispatcher.utter_message(text=f"Query result: {result}")
        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
        finally:
            if connection:
                connection.close()




# class ActionDetectLanguage(Action):
#     def name(self) -> str:
#         return "action_detect_language"

#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
#         user_message = tracker.latest_message.get("text")  # Get the user's latest message
        
#         # Detect the language
#         try:
#             detected_language = detect(user_message)  # Returns 'en', 'fr', etc.
#         except LangDetectException:
#             detected_language = "en"  # Default to English if detection fails
        
#         # Map detected language to slot value ('en' or 'fr')
#         language = "fr" if detected_language == "fr" else "en"
        
#         # Set the language slot
#         return [SlotSet("language", language)]



class DatabaseAction(Action):
    def name(self) -> str:
    # def connect_db(self):
        # Establish a connection to PostgreSQL
        return psycopg2.connect(
            dbname="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

class ActionContributeToTontine(Action):
    def name(self) -> Text:
        return "action_contribute_to_tontine"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the slot values
        tontine_name = tracker.get_slot("tontine_name")
        contribution_amount = tracker.get_slot("contribution_amount")
        user_id = tracker.get_slot("user_id")

        # Check if required slots are filled
        if not tontine_name or not contribution_amount or not user_id:
            dispatcher.utter_message(text="Please provide all required details (tontine name, amount, and user ID).")
            return []

        connection = None
        cursor = None

        try:
            # Connect to PostgreSQL database
            connection = psycopg2.connect(
                dbname="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost"
            )
            cursor = connection.cursor()

            # Check if tontine exists
            cursor.execute("SELECT * FROM tontines WHERE tontine_name = %s", (tontine_name,))
            tontine = cursor.fetchone()

            if tontine:
                # Record the contribution
                cursor.execute(
                    "INSERT INTO contributions (user_id, tontine_name, amount) VALUES (%s, %s, %s)",
                    (user_id, tontine_name, contribution_amount)
                )
                connection.commit()
                dispatcher.utter_message(text=f"Thank you! Your contribution of {contribution_amount} has been added.")
            else:
                dispatcher.utter_message(text=f"Tontine {tontine_name} does not exist.")

        except Exception as e:
            dispatcher.utter_message(response="utter_contribution_failed")
            print(f"Error: {e}")

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()


        return []

class ActionJoinTontine(Action):
    def name(self) -> Text:
        return "action_join_tontine"

    def connect_db(self):
        # Establish connection to PostgreSQL database
        return psycopg2.connect(
            database="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Get the slot values
        tontine_name = tracker.get_slot("name_tontine")
        user_id = tracker.get_slot("user_id")


 # Check if the required slots are filled
        if not tontine_name:
            dispatcher.utter_message(text="Please provide a valid tontine name.")
            return []

        if not user_id:
            dispatcher.utter_message(text="Please provide your user ID.")
            return []

        try:
            with self.connect_db() as connection:
                with connection.cursor() as cursor:
                    # Find the tontine ID based on the tontine name
                    query = """
                        SELECT tontine_id FROM tontines WHERE tontine_name = %s AND status = 'open'
                    """
                    cursor.execute(query, (tontine_name,))
                    tontine_id = cursor.fetchone()

            if tontine_id:
                # Add user to the tontine
                insert_query = """
                    INSERT INTO tontine_members (tontine_id, user_id, join_date, status)
                    VALUES (%s, %s, NOW(), 'active')
                """
                cursor.execute(insert_query, (tontine_id[0], user_id))
                connection.commit()

                # dispatcher.utter_message(text=f"You have successfully joined the tontine '{tontine_name}'.")
                dispatcher.utter_message(response="utter_join_success")
            else:
                dispatcher.utter_message(text="The tontine is no longer open or doesn't exist.")

        except (Exception, psycopg2.DatabaseError) as error:
            dispatcher.utter_message(text="An error occurred while joining the tontine.")
            print(f"Error: {error}")

        finally:
            if connection:
                connection.close()

        return []

class ActionCheckBalance(Action):
    def name(self) -> Text:
        return "action_check_balance"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        user_id = tracker.get_slot("user_id")

                # Check if user_id is empty or invalid
        if not user_id or user_id.strip() == "":
            dispatcher.utter_message(text="Please provide a valid user ID.")
            return []

        try:
            # Connect to PostgreSQL database
            connection = psycopg2.connect(
                dbname="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost"
            )
            cursor = connection.cursor()

            # Query balance for user_id
            cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
            user_balance = cursor.fetchone()

            if user_balance:
                balance = user_balance[0]
                dispatcher.utter_message(text=f"Your current balance is {balance}.")
                # dispatcher.utter_message(response="utter_show_balance")
                return [SlotSet("balance", balance)]
            else:
                dispatcher.utter_message(text="Sorry, we couldn't find your balance.")

        except Exception as e:
            dispatcher.utter_message(response="utter_balance_check_failed")
            print(f"Error: {e}")

        finally:
            cursor.close()
            connection.close()

        return []

class ActionCreateNewTontine(Action):
    def name(self) -> Text:
        return "action_confirm_tontine_creation"

    def connect_db(self):
        # Establish connection to PostgreSQL database
        return psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
        )

    def insert_tontine(self, tontine_new_name, tontine_type, tontine_duration, contribution_frequency,
                       new_contribution_amount, payout_strategy, purpose, target_audience,
                       starting_currency, amount_to_receive):
        conn = None
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            insert_query = """
                INSERT INTO tontines (tontine_name, tontine_type, tontine_duration,
                                      contribution_frequency, contribution_amount,
                                      payout_strategy, purpose, target_audience,
                                      starting_currency, amount_to_receive)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (tontine_new_name, tontine_type, tontine_duration, contribution_frequency,
                                          new_contribution_amount, payout_strategy, purpose, target_audience,
                                          starting_currency, amount_to_receive))
            conn.commit()
            cursor.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Database error: {error}")
        finally:
            if conn:
                conn.close()

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        tontine_new_name = tracker.get_slot("tontine_new_name")
        tontine_type = tracker.get_slot("tontine_type")
        tontine_duration = tracker.get_slot("tontine_duration")
        contribution_frequency = tracker.get_slot("contribution_frequency")
        new_contribution_amount = tracker.get_slot("new_contribution_amount")
        payout_strategy = tracker.get_slot("payout_strategy")
        purpose = tracker.get_slot("purpose")
        target_audience = tracker.get_slot("target_audience")
        starting_currency = tracker.get_slot("starting_currency")
        amount_to_receive = tracker.get_slot("amount_to_receive")

        # Insert tontine details into the database
        self.insert_tontine(tontine_new_name, tontine_type, tontine_duration, contribution_frequency,
                            new_contribution_amount, payout_strategy, purpose, target_audience,
                            starting_currency, amount_to_receive)

        # Inform the user of successful creation
        # dispatcher.utter_message(text=f"The tontine '{tontine_new_name}' has been successfully created.")
        dispatcher.utter_message(response="utter_confirm_tontine_creation")
        return [SlotSet("tontine_new_name", None), SlotSet("tontine_type", None), SlotSet("tontine_duration", None),
                SlotSet("contribution_frequency", None), SlotSet("new_contribution_amount", None),
                SlotSet("payout_strategy", None), SlotSet("purpose", None),
                SlotSet("target_audience", None), SlotSet("starting_currency", None),
                SlotSet("amount_to_receive", None)]

class ActionListTontineOptions(Action):
    def name(self) -> Text:
        return "action_list_tontine_options"

    def connect_db(self):
        return psycopg2.connect(
            database="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        tontine_type = tracker.get_slot("tontine_type")
        tontine_duration = tracker.get_slot("tontine_duration")

        try:
            connection = self.connect_db()
            cursor = connection.cursor()

            # Fetch tontines that match the specified type and duration
            query = """
                SELECT tontine_name, tontine_type, tontine_duration, contribution_frequency
                FROM tontines
                WHERE tontine_type = %s AND tontine_duration = %s
            """
            cursor.execute(query, (tontine_type, tontine_duration))
            tontines = cursor.fetchall()

            if tontines:
                response = "Here are the tontines that match your preferences:\n"
                for tontine in tontines:
                    response += f"- {tontine[0]} ({tontine[1]} - {tontine[2]})\n"
                dispatcher.utter_message(text=response)
            else:
                dispatcher.utter_message(text="Sorry, no tontine options match your criteria.")

        except (Exception, psycopg2.DatabaseError) as error:
            dispatcher.utter_message(text="An error occurred while fetching tontine options.")
            print(f"Error: {error}")

        finally:
            if connection:
                connection.close()

        return []

class ActionAccessOpenTontineServices(Action):
    def name(self) -> Text:
        return "action_access_open_tontine_services"

    def connect_db(self):
        return psycopg2.connect(
            database="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        try:
            connection = self.connect_db()
            cursor = connection.cursor()

            # Query to fetch open tontines
            query = """
                SELECT tontine_name, tontine_type, tontine_duration, contribution_frequency, status
                FROM tontines
                WHERE status = 'open'
            """
            cursor.execute(query)
            tontines = cursor.fetchall()

            if tontines:
                response = "Here are the open tontines:\n"
                for tontine in tontines:
                    response += f"- {tontine[0]} ({tontine[1]} - {tontine[2]} - {tontine[3]})\n"
                dispatcher.utter_message(text=response)
            else:
                dispatcher.utter_message(text="Currently, there are no open tontines available.")

        except (Exception, psycopg2.DatabaseError) as error:
            dispatcher.utter_message(text="An error occurred while fetching open tontine services.")
            print(f"Error: {error}")

        finally:
            if connection:
                connection.close()

        return []

class ActionCreateProjectTontine(Action):
    def name(self) -> Text:
        return "action_create_project_tontine"

    def connect_db(self):
        return psycopg2.connect(
            database="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Retrieve slot values
        project_name = tracker.get_slot("project_name")
        tontine_type = tracker.get_slot("tontine_type")
        contribution_frequency = tracker.get_slot("contribution_frequency")
        amount = tracker.get_slot("amount")
        duration = tracker.get_slot("duration")
        payout_strategy = tracker.get_slot("payout_strategy")
        target_audience = tracker.get_slot("target_audience")
        starting_currency = tracker.get_slot("starting_currency")
        amount_to_receive = tracker.get_slot("amount_to_receive")
        purposes = tracker.get_slot("purposes")

        try:
            connection = self.connect_db()
            cursor = connection.cursor()

            # Insert new tontine into the database
            query = """
                INSERT INTO project_tontines (project_name, tontine_type, contribution_frequency, amount,
                                      duration, payout_strategy, target_audience, starting_currency,
                                      amount_to_receive, purposes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (project_name, tontine_type, contribution_frequency, amount,
                                   duration, payout_strategy, target_audience, starting_currency,
                                   amount_to_receive, purposes))
            connection.commit()

            dispatcher.utter_message(text=f"The project tontine '{project_name}' has been created successfully.")
        except (Exception, psycopg2.DatabaseError) as error:
            dispatcher.utter_message(text="There was an error while creating the project tontine.")
            print(f"Error: {error}")
        finally:
            if connection:
                connection.close()

        return []

class ActionContributeToProjectTontine(Action):
    def name(self) -> Text:
        return "action_contribute_to_project_tontine"

    def connect_db(self):
        return psycopg2.connect(
            database="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432"
        )

    def insert_contribution(self, project_name, contribution_amount, user_id):
        conn = None
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            insert_query = """
                INSERT INTO contributions (project_name, contribution_amount, user_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (project_name, contribution_amount, user_id))
            conn.commit()
            cursor.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Database error: {error}")
        finally:
            if conn:
                conn.close()

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        project_name = tracker.get_slot("project_name")
        contribution_amount = tracker.get_slot("contribution_amount")
        user_id = tracker.get_slot("user_id")

        # Check if all required slots are provided
        if not project_name or not contribution_amount or not user_id:
            dispatcher.utter_message(text="I need the project name, contribution amount, and your user ID to proceed.")
            return []

        # Insert the contribution into the database
        self.insert_contribution(project_name, contribution_amount, user_id)

        # Inform the user of successful contribution
        dispatcher.utter_message(text=f"Your contribution of {contribution_amount} to the project called {project_name} has been successfully recorded.")

        return [SlotSet("project_name", None), SlotSet("contribution_amount", None), SlotSet("user_id", None)]

class ActionMakeSwapRequest(Action):
    def name(self) -> Text:
        return "action_make_swap_request"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Retrieve details from slots
        starting_currency = tracker.get_slot('starting_currency')
        target_currency = tracker.get_slot('target_currency')
        starting_amount = tracker.get_slot('starting_amount')
        amount_to_receive = tracker.get_slot('amount_to_receive')

        # Check each required field
        if not starting_currency:
            dispatcher.utter_message(text="Please provide your starting currency.")
            return []
        if not target_currency:
            dispatcher.utter_message(text="Please specify the currency that you wish to obtain.")
            return []
        if not starting_amount:
            dispatcher.utter_message(text="Please enter the starting amount you wish to swap.")
            return []
        if not amount_to_receive:
            dispatcher.utter_message(text="Please enter the amount you wish to receive after swapping.")
            return []

        # Inform the user about the deduction
        deduction_percentage = 4.76
        dispatcher.utter_message(
            text=f"Please note that a {deduction_percentage}% fee will be deducted from your starting amount."
        )

        # Calculate the amount after deduction
        amount_after_deduction = float(starting_amount) - (float(starting_amount) * (deduction_percentage / 100))

        # Save the swap request to the database
        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Insert the swap request into the database
            cursor.execute("""
                INSERT INTO swap_requests (starting_currency, target_currency, starting_amount, amount_to_receive, amount_after_deduction)
                VALUES (%s, %s, %s, %s, %s)
            """, (starting_currency, target_currency, starting_amount, amount_to_receive, amount_after_deduction))

            # Commit the transaction
            connection.commit()
            dispatcher.utter_message(text=f"Your swap request from {starting_amount} {starting_currency} to {target_currency} has been processed and saved!")

        except Exception as e:
            dispatcher.utter_message(text="There was an error saving your swap request. Please try again.")
            print(f"Database error: {e}")
        finally:
            # Close the cursor and connection
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionListPendingSwaps(Action):

    def name(self) -> Text:
        return "action_list_pending_swaps"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        swap_id = tracker.get_slot("swap_id")
        user_id = tracker.get_slot("user_id")  # Ensure user_id is set if required

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Query to retrieve pending swaps (adjust as necessary)
            if swap_id:
                cursor.execute("""
                    SELECT starting_currency, target_currency, starting_amount, amount_to_receive 
                    FROM swap_requests 
                    WHERE status = 'pending' AND swap_id = %s
                """, (swap_id,))
            else:
                cursor.execute("""
                    SELECT starting_currency, target_currency, starting_amount, amount_to_receive 
                    FROM swap_requests 
                    WHERE status = 'pending' AND user_id = %s
                """, (user_id,))

            pending_swaps = cursor.fetchall()

            if pending_swaps:
                swaps_text = "\n".join(
                    [f"{start_amt} {start_curr} to {target_amt} {target_curr}" for start_curr, target_curr, start_amt, target_amt in pending_swaps]
                )
                dispatcher.utter_message(template="utter_pending_swaps_list", pending_swaps=swaps_text)
            else:
                dispatcher.utter_message(template="utter_no_pending_swaps")

        except Exception as e:
            dispatcher.utter_message(text="There was an error retrieving your pending swaps. Please try again later.")
            print(f"Database error: {e}")
        
        finally:
            # Close the database connection
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionProcessPayment(Action):
    def name(self) -> Text:
        return "action_process_payment"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        payment_amount = tracker.get_slot("payment_amount")
        phone_number = tracker.get_slot("phone_number")  
        user_id = tracker.get_slot("user_id")  # Assume user_id is provided

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Insert payment record into the database
            cursor.execute("""
                INSERT INTO payments (user_id, payment_amount, phone_number)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (user_id, payment_amount, phone_number))

            payment_id = cursor.fetchone()[0]
            connection.commit()

            dispatcher.utter_message(
                text=f"Your payment of {payment_amount} to {phone_number} was successful. Transaction ID: {payment_id}"
            )

        except Exception as e:
            dispatcher.utter_message(text="There was an error processing your payment. Please try again.")
            print(f"Database error: {e}")

        finally:
            # Close the database connection
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        # Clear the slots after the transaction
        return [
            SlotSet("payment_amount", None),
            SlotSet("phone_number", None)
        ]

class ActionManageAccount(Action):

    def name(self) -> Text:
        return "action_manage_account"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_id = tracker.get_slot("user_id")  # Make sure user_id slot is filled
        
        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Retrieve account information
            cursor.execute("SELECT * FROM user_accounts WHERE user_id = %s", (user_id,))
            account_info = cursor.fetchone()

            if account_info:
                dispatcher.utter_message(
                    text=f"Here are your account details: {account_info}. What would you like to update?"
                )
            else:
                dispatcher.utter_message(
                    text="I couldn't find your account information. Please ensure your account is set up correctly."
                )

        except Exception as e:
            dispatcher.utter_message(text="There was an error accessing your account. Please try again later.")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []
    
class ActionChangePassword(Action):

    def name(self) -> Text:
        return "action_change_password"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        current_password = tracker.get_slot("current_password")
        new_password = tracker.get_slot("new_password")
        user_id = tracker.get_slot("user_id")  # Ensure user_id slot is set if required

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Check if the current password matches the one in the database
            cursor.execute("SELECT password FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()

            if result and result[0] == current_password:
                # Update the password
                cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password, user_id))
                connection.commit()
                dispatcher.utter_message(template="utter_password_change_success")
            else:
                dispatcher.utter_message(text="Your current password is incorrect. Please try again.")

        except Exception as e:
            dispatcher.utter_message(template="utter_password_change_failed")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionForgotPassword(Action):
    def name(self) -> Text:
        return "action_reset_password"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Check if the email exists in the database
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                # Generate a password reset token
                reset_token = str(uuid.uuid4())

                # Save the reset token to the database (optional: add expiration timestamp)
                cursor.execute("""
                    INSERT INTO password_reset_tokens (user_id, token, created_at)
                    VALUES (%s, %s, NOW())
                """, (user[0], reset_token))
                connection.commit()

                # Send email with reset link
                reset_link = f"http://example.com/reset-password?token={reset_token}"
                sender_email = "noreply@example.com"
                sender_password = "your_email_password"
                subject = "Password Reset Request"

                # Compose email
                message = MIMEMultipart()
                message["From"] = sender_email
                message["To"] = email
                message["Subject"] = subject
                body = f"""
                Hi,

                We received a request to reset your password. Click the link below to reset it:

                {reset_link}

                If you didn't request this, please ignore this email.

                Regards,
                Toupesu Support
                """
                message.attach(MIMEText(body, "plain"))

                # Send email
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(message)

                dispatcher.utter_message(template="utter_password_reset_email_sent")
            else:
                dispatcher.utter_message(template="utter_email_not_found")

        except Exception as e:
            dispatcher.utter_message(template="utter_reset_error")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionEditName(Action):
    def name(self) -> Text:
        return "action_edit_name"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")
        new_name = tracker.get_slot("new_name")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Check if the email exists in the database
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                # Update the user's name in the database
                cursor.execute("""
                    UPDATE users SET name = %s WHERE email = %s
                """, (new_name, email))
                connection.commit()

                dispatcher.utter_message(template="utter_name_update_successful")
            else:
                dispatcher.utter_message(template="utter_email_not_found")

        except Exception as e:
            dispatcher.utter_message(template="utter_name_update_failed")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionSetLanguage(DatabaseAction):
    def name(self) -> Text:
        return "action_set_language"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Get the language entity from the user's input
        language = next(tracker.get_latest_entity_values("language"), None)
        
        # Database connection and cursor
        connection = None
        cursor = None

        try:
            # Connect to the database
            connection = self.connect_db()
            if not connection:
                dispatcher.utter_message(text="Unable to connect to the database.")
                return []

            cursor = connection.cursor()

            # Supported languages
            supported_languages = ["English", "French", "Spanish", "German", "Italian", "Portuguese", "Arabic", "Dutch", "Chinese", "Russian"]

            if language in supported_languages:
                # Store the user's language preference in the database
                user_id = tracker.get_slot("user_id")
                cursor.execute(
                    sql.SQL("UPDATE users SET preferred_language = %s WHERE user_id = %s"),
                    (language, user_id)
                )
                connection.commit()

                # Inform the user of the successful language change
                dispatcher.utter_message(text=f"Your preferred language has been updated to {language}.")
                return [SlotSet("language", language)]
            else:
                dispatcher.utter_message(text=f"The language '{language}' is not supported. Please choose from the following: {', '.join(supported_languages)}.")

        except psycopg2.DatabaseError as db_error:
            dispatcher.utter_message(text="Database error occurred while updating the language.")
            print(f"Database error: {db_error}")
        except Exception as error:
            dispatcher.utter_message(text="An unexpected error occurred while updating the language.")
            print(f"Error: {error}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return [SlotSet("language", None)]  # Reset the language slot if necessary

class ActionTopUpBalance(Action):
    def name(self) -> Text:
        return "action_top_up_balance"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")
        top_up_amount = tracker.get_slot("top_up_amount")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Check if the email exists in the database
            cursor.execute("SELECT id, balance FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                # Get the current balance
                current_balance = user[1]
                # Calculate the new balance
                new_balance = current_balance + top_up_amount

                # Update the user's balance in the database
                cursor.execute("""
                    UPDATE users SET balance = %s WHERE email = %s
                """, (new_balance, email))
                connection.commit()

                dispatcher.utter_message(template="utter_balance_top_up_successful")
            else:
                dispatcher.utter_message(template="utter_email_not_found")

        except Exception as e:
            dispatcher.utter_message(template="utter_balance_top_up_failed")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionMakeWithdrawal(Action):
    def name(self) -> Text:
        return "action_make_withdrawal"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")
        withdrawal_amount = tracker.get_slot("withdrawal_amount")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Check if the email exists in the database
            cursor.execute("SELECT id, balance FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                # Get the current balance
                current_balance = user[1]

                # Check if the balance is sufficient for the withdrawal
                if current_balance >= withdrawal_amount:
                    # Calculate the new balance
                    new_balance = current_balance - withdrawal_amount

                    # Update the user's balance in the database
                    cursor.execute("""
                        UPDATE users SET balance = %s WHERE email = %s
                    """, (new_balance, email))
                    connection.commit()

                    dispatcher.utter_message(template="utter_balance_withdraw_successful")
                else:
                    dispatcher.utter_message(template="utter_balance_insufficient_funds")
            else:
                dispatcher.utter_message(template="utter_email_not_found")

        except Exception as e:
            dispatcher.utter_message(template="utter_balance_withdraw_failed")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionListTransactions(Action):
    def name(self) -> Text:
        return "action_list_transactions"

    def connect_db(self):
        return psycopg2.connect(
            dbname="toupesu_db",
            user="postgres",
            password="admin",
            host="localhost"
        )

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        account_id = tracker.get_slot("account_id")

        if not account_id:
            dispatcher.utter_message(response="utter_ask_account_id")
            return []

        connection = None
        cursor = None

        try:
            connection = self.connect_db()
            cursor = connection.cursor()

            # Query to fetch transactions
            query = """
                SELECT transaction_date, amount, transaction_type
                FROM transactions
                WHERE account_id = %s
                ORDER BY transaction_date DESC
                LIMIT 5
            """
            cursor.execute(query, (account_id,))
            transactions = cursor.fetchall()

            if transactions:
                transaction_list = "\n".join(
                    [f"{t[0]} - {t[1]} ({t[2]})" for t in transactions]
                )
                dispatcher.utter_message(
                    text=f"Here are your recent transactions:\n{transaction_list}"
                )
            else:
                dispatcher.utter_message(
                    text="No recent transactions found for the provided account ID."
                )

        except Exception as e:
            dispatcher.utter_message(response="utter_list_transactions_failure")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionFileComplaint(Action):
    def name(self) -> Text:
        return "action_file_complaint"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        complaint_topic = tracker.get_slot("complaint_topic")
        user_id = tracker.get_slot("user_id")  # Assume user_id is stored in slots

        if not complaint_topic:
            dispatcher.utter_message(text="Could you please specify the complaint topic?")
            return []

        connection = None
        cursor = None

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                dbname="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost"
            )
            cursor = connection.cursor()

            # Insert the complaint record
            cursor.execute(
                "INSERT INTO complaints (user_id, complaint_topic) VALUES (%s, %s)",
                (user_id, complaint_topic)
            )
            connection.commit()

            dispatcher.utter_message(response="utter_complaint_success", complaint_topic=complaint_topic)

        except Exception as e:
            dispatcher.utter_message(response="utter_complaint_failed")
            print(f"Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionGetPendingSwaps(Action):

    def name(self) -> Text:
        return "action_get_pending_swaps"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_id = tracker.get_slot("user_id")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Query to retrieve pending swaps for the user
            cursor.execute("""
                SELECT swap_id, starting_currency, target_currency, starting_amount, amount_to_receive 
                FROM swap_requests 
                WHERE status = 'pending' AND user_id = %s
            """, (user_id,))

            pending_swaps = cursor.fetchall()

            # If there are pending swaps, send them to the user
            if pending_swaps:
                swaps_text = "\n".join(
                    [f"Swap ID: {swap[0]}, {swap[3]} {swap[1]} to {swap[4]} {swap[2]}" for swap in pending_swaps]
                )
                dispatcher.utter_message(text=f"Here are your pending swaps:\n{swaps_text}")
            else:
                dispatcher.utter_message(text="You have no pending swaps at the moment.")

        except Exception as e:
            dispatcher.utter_message(text="There was an error retrieving your pending swaps. Please try again later.")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionCancelSwap(Action):

    def name(self) -> Text:
        return "action_cancel_swap"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        swap_id = tracker.get_slot("swap_id")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Update the status of the swap to 'cancelled'
            cursor.execute("""
                UPDATE swap_requests 
                SET status = 'cancelled'
                WHERE swap_id = %s
            """, (swap_id,))

            connection.commit()

            dispatcher.utter_message(text=f"Swap {swap_id} has been successfully cancelled.")

        except Exception as e:
            dispatcher.utter_message(text="There was an error cancelling the swap. Please try again later.")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionConfirmSwap(Action):

    def name(self) -> Text:
        return "action_confirm_swap"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        swap_id = tracker.get_slot("swap_id")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Update the status of the swap to 'confirmed'
            cursor.execute("""
                UPDATE swap_requests 
                SET status = 'confirmed'
                WHERE swap_id = %s
            """, (swap_id,))

            connection.commit()

            dispatcher.utter_message(text=f"Swap {swap_id} has been confirmed.")

        except Exception as e:
            dispatcher.utter_message(text="There was an error confirming the swap. Please try again later.")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

class ActionRejectSwap(Action):

    def name(self) -> Text:
        return "action_reject_swap"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        swap_id = tracker.get_slot("swap_id")

        try:
            # Connect to the PostgreSQL database
            connection = psycopg2.connect(
                database="toupesu_db",
                user="postgres",
                password="admin",
                host="localhost",
                port="5432"
            )
            cursor = connection.cursor()

            # Update the status of the swap to 'rejected'
            cursor.execute("""
                UPDATE swap_requests 
                SET status = 'rejected'
                WHERE swap_id = %s
            """, (swap_id,))

            connection.commit()

            dispatcher.utter_message(text=f"Swap {swap_id} has been rejected.")

        except Exception as e:
            dispatcher.utter_message(text="There was an error rejecting the swap. Please try again later.")
            print(f"Database error: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return []

