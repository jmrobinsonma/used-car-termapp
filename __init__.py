import os
import sys
import csv
import click
import smtplib
import colorama
import pyfiglet
import termcolor
from time import sleep
from flask import jsonify
from progressbar import ProgressBar
from datetime import datetime
from bs4 import BeautifulSoup
from requests import get
from sqlalchemy import create_engine, exc, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from email.message import EmailMessage

colorama.init()

Base = declarative_base()
class Posts(Base):

    __tablename__ = "posts"

    timing = Column(String(120), unique=False, nullable=False, primary_key=True)
    title_text = Column(String(120), unique=False, nullable=False)
    price = Column(String(120), unique=False, nullable=False)
    link = Column(String(120), unique=False, nullable=False)

    def __repr__(self):
        return f"{self.timing}\n{self.title_text}\n{self.price}\n{self.link}\n"

class DealScraper:


    def __init__(self,urls,name,session=False,instance_filename="",EMAIL_ADDRESS="",EMAIL_PASSWORD="",\
                    instance_responses=(),instance_results=(),post_timing=[],post_title_texts=[],\
                    post_prices=[],post_links=[],num_posts=0,new_results=0):
        self.urls = urls
        self.name = name
        self.session = False
        self.instance_filename = ""
        self.instance_responses = ()
        self.instance_results = ()
        self.post_timing = []
        self.post_title_texts = []
        self.post_prices = []
        self.post_links = []
        self.num_posts = 0
        self.new_results = 0
        self.total_db_posts = 0
        self.choice = ''
        self.EMAIL_ADDRESS = ""
        self.EMAIL_PASSWORD = ""


    def get_results(self):

        try:
            for url in self.urls:
                response = get(url)
                soup = BeautifulSoup(response.text,'html.parser')
                posts = soup.find_all('li',class_='result-row')

                for post in posts:
                    post_title = post.find('p', class_='result-info')
                    post_link = post_title.a['href']
                    region = bool(post_link.split('/')[2].split('.')[0]=='westernmass')

                    if region:
                        self.num_posts += 1

                        post_title_text = post_title.text.split('\n')[5]
                        self.post_title_texts.append(post_title_text)

                        post_link = post_title.a['href']
                        self.post_links.append(post_link)

                        post_price = post_title.find('span',class_='result-price').text
                        self.post_prices.append(post_price)

                        post_datetime = post.find('time', class_= 'result-date')['datetime']
                        self.post_timing.append(post_datetime)
        except Exception as e:
            print(f"{e}")
        if self.num_posts:
            self.instance_results = (self.post_timing, self.post_title_texts, self.post_prices, self.post_links, self.num_posts)
            return self.instance_results
        else:
            sys.exit()

    def db_connect(self):
        try:
            engine = create_engine(f'sqlite:////home/jrob/databases/{self.name}.db')  #echo=True for output to console
            Base.metadata.create_all(bind=engine)
            Session = sessionmaker(bind=engine)
            self.session = Session()
        except Exception as e:
            print(f"\nThere was a problem connecting to the database!\n--> {e}")

    def db_all(self, session):
        all_posts = self.session.query(Posts).all()
        self.total_db_posts = len(all_posts)
        print(f"""
            ***ALL RESULTS***
            """)
        for result in all_posts:
           print(result)
        print(f"{len(all_posts)} total stored posts")

    def db_last_ten(self, session):
        last_ten = self.session.query(Posts).all()[-10:]
        print(f"""
            ***LAST TEN RESULTS***
            """)
        for result in last_ten:
           print(result)

    def db_update(self, instance_results, session):
        post_timing, post_title_texts, post_prices, post_links, num_posts = instance_results
        duplicates = 0

        try:
            for i in range(len(post_links)):
                try:
                    post = Posts()
                    post.timing = post_timing[i]
                    post.title_text = post_title_texts[i]
                    post.price = post_prices[i]
                    post.link = post_links[i]
                    self.session.add(post)
                    self.session.commit()
                except exc.IntegrityError as e:
                    duplicates += 1
                    self.session.rollback()
            self.new_results = num_posts - duplicates
            return self.new_results
        except Exception as e:
            print(f"\nThere was a problem updating the database!\n--> {e}")

    def show_num_results(self, new_results, instance_results):
        post_timing, post_title_texts, post_prices, post_links, num_posts = instance_results

        print(f"""
            ***CURRENT RESULTS***
{self.new_results} New results
            """)
        for result in range(num_posts):
            print(f"Result {result + 1}\n{post_title_texts[result]}\n{post_prices[result]}\n{post_links[result]}\n")

    def db_close(self, session):
        self.session.close()

    def create_filename(self):
        try:
            date_time = str(datetime.now()).split('.')[0]
            self.instance_filename = f"{date_time}_{self.name}.csv"
        except Exception as e:
            print(f"\nThere was a problem creating a filename for your csv file!\n--> {e}")


    def create_csv(self, instance_filename, instance_results):
        print("Creating csv File...")

        post_timing, post_title_texts, post_prices, post_links, num_posts = instance_results

        try:
            with open(self.instance_filename, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(['Posted','Post Title','Price','URL'])
                for i,v in enumerate(range(len(post_links))):
                    csv_writer.writerow([post_timing[i],
                                        post_title_texts[i],
                                        post_prices[i],
                                        post_links[i]])
            print(f"Created {self.instance_filename}")
        except Exception as e:
            print(f"\nThere was a problem creating a csv file!\n--> {e}")


    def get_cred(self):

        try:
            self.EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
            if not self.EMAIL_ADDRESS:
                print("\nThere was a problem obtaining environment variable for username and an email will not be sent!")
                print("*tip* try running 'source ~/.bash_profile' command")
                print("GoodBye!")
                sys.exit()
        except Exception as e:
            print(f"\nThere was a problem obtaining environment variable for your username!\n\
                        *tip* try running 'source ~/.bash_profile' command")
        try:
            self.EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')
            if not self.EMAIL_PASSWORD:
                print("\nThere was a problem obtaining environment variable for your password and an email will not be sent!")
                print("*tip try running 'source ~/.bash_profile' command")
                print("GoodBye!")
                sys.exit()
        except Exception as e:
            print(f"\nThere was a problem obtaining environment variable for your password!\n--> {e}\n\
                        *tip* try running 'source ~/.bash_profile' command")
        return self.EMAIL_ADDRESS, self.EMAIL_PASSWORD


    def send_mail(self, EMAIL_ADDRESS, EMAIL_PASSWORD, instance_filename):
        print("Preparing email...")

        msg = EmailMessage()
        msg['Subject'] = f"{self.name}"
        msg['From'] = self.EMAIL_ADDRESS
        msg['to'] = self.EMAIL_ADDRESS
        msg.set_content('Csv attached...')

        try:
            with open(self.instance_filename, 'rb') as f:
                file = f.read()
            msg.add_attachment(file, maintype='application', subtype='octet-stream', filename=instance_filename)
        except Exception as e:
            print(f"\nThere was a problem while adding a csv file to your email!\n--> {e}")

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.EMAIL_ADDRESS, self.EMAIL_PASSWORD)
                smtp.send_message(msg)
            print("Email Sent")
        except Exception as e:
            print(f"\nThere was a problem while attempting to send your email!\n--> {e}")

    def delete_csv(self, instance_filename):
        try:
            os.remove(self.instance_filename)
        except Exception as e:
            print(f"\nThere was a problem deleting the csv file after sending your email!\n--> {e}")

    def greeting(self):
        header = pyfiglet.figlet_format("DEAL\nSCRAPER", font='slant')
        text = termcolor.colored(header, color='yellow', attrs=['bold'])
        print(text)
#        bar = ProgressBar()
#        for i in bar(range(50)):
#            sleep(0.02)


    def user_choice(self):
        self.choice = click.prompt(f"""
There are {self.new_results} new results
Press 't' for last ten posts, 'a' for all stored posts, or 'q' to quit()
""", type=click.Choice(['t','a','q'], case_sensitive=True))
        return self.choice

urls = ["https://westernmass.craigslist.org/search/cta?query=subaru+forester&hasPic=1&max_price=5000&auto_transmission=1",
            "https://westernmass.craigslist.org/search/cta?hasPic=1&postedToday=1&max_price=5000&auto_transmission=1",
            "https://westernmass.craigslist.org/search/cta?query=honda+crv&hasPic=1&max_price=5000&auto_transmission=1",
            "https://westernmass.craigslist.org/search/cta?query=toyota+rav4&hasPic=1&max_price=5000&auto_transmission=1"]
def main():

    find_used_cars = DealScraper(urls, "used-cars")
    find_used_cars.greeting()
    find_used_cars.get_results()
    find_used_cars.db_connect()
    find_used_cars.show_num_results(find_used_cars.new_results,find_used_cars.instance_results)
    find_used_cars.user_choice()

    if find_used_cars.choice == 't':
        find_used_cars.db_last_ten(find_used_cars.session)
        find_used_cars.db_close(find_used_cars.session)

    elif find_used_cars.choice == 'a':
        find_used_cars.db_all(find_used_cars.session)
        find_used_cars.db_close(find_used_cars.session)

    else:
        EMAIL_ADDRESS,EMAIL_PASSWORD = (find_used_cars.get_cred())
        confirm_email = input(f"\nSend Email to {EMAIL_ADDRESS} with the current results? y/n: ")
        condition_not_met = True
        while condition_not_met:
            if confirm_email == "y":
                try:
                    find_used_cars.create_filename()
                    find_used_cars.create_csv(find_used_cars.instance_filename, find_used_cars.instance_results)
                    find_used_cars.send_mail(EMAIL_ADDRESS,EMAIL_PASSWORD, find_used_cars.instance_filename)
                    find_used_cars.delete_csv(find_used_cars.instance_filename)
                    condition_not_met = False
                except Exception as e:
                    print(f"There was an error!\n---> {e}")
            elif confirm_email == "n":
                print("No email sent")
                condition_not_met = False
            else:
                confirm_email = input(f"\nSend Email to {EMAIL_ADDRESS} with these results? y/n: \n*** Please enter 'y' or 'n' ***: ")

    find_used_cars.db_update(find_used_cars.instance_results, find_used_cars.session)
    find_used_cars.db_close(find_used_cars.session)

    sys.exit()

if __name__ == '__main__':
    main()
