# ✈️ SkyBook — თვითმფრინავის ბილეთების დაჯავშნა

IT Step Academy-ის ფინალური პროექტი — ავიაბილეთების ონლაინ დაჯავშნის ვებ აპლიკაცია.

**ტექნოლოგიები:** Python · Django · SQL (SQLite) · HTML · CSS · JavaScript

## ფუნქციონალი

- **რეგისტრაცია / ავტორიზაცია** — სახელი, გვარი, ტელეფონი, ელ-ფოსტა, პაროლი; შესვლა ელ-ფოსტით
- **მთავარი გვერდი** — ძიების ველი (საიდან / სად / თარიღი) და ყველაზე იაფი ფრენები
- **ძიება და ფილტრაცია** — ქალაქი, თარიღი, ავიაკომპანია, მაქსიმალური ფასი, მხოლოდ პირდაპირი ფრენები, დალაგება
- **ფრენის გვერდი** — დეტალური ინფორმაცია, ადგილების სქემა (ეკონომი / ბიზნესი), მგზავრების მონაცემები, ფასის ავტომატური დათვლა
- **დაჯავშნა** — ერთ ჯავშანზე 6 მგზავრამდე; ერთი და იგივე ადგილის ორჯერ დაჯავშნა შეუძლებელია
- **პროფილი** — ჩემი ჯავშნები (გაუქმების შესაძლებლობით) და შენახული ფრენები
- **ადმინ პანელი** — ქალაქების, ავიაკომპანიების, ფრენებისა და ჯავშნების მართვა

## REST API

პასუხები JSON ფორმატშია. დოკუმენტაცია: `/api/`

| მეთოდი | მისამართი | აღწერა |
|---|---|---|
| GET | `/api/cities/` | ქალაქები / აეროპორტები |
| GET | `/api/airlines/` | ავიაკომპანიები |
| GET | `/api/flights/?from=TBS&to=IST&date=2026-11-20` | ფრენების ძიება (ასევე: `airline`, `max_price`, `direct=1`, `cabin`) |
| GET | `/api/flights/<id>/` | ფრენა, თავისუფალი/დაკავებული ადგილები, ბარგის პირობები |
| GET | `/api/tickets/<ნომერი>/?last_name=...` | ბილეთის შემოწმება |

## ბაზის სტრუქტურა

| ცხრილი | აღწერა |
|---|---|
| `User` | მომხმარებელი (ელ-ფოსტა, ტელეფონი) |
| `City` | ქალაქი / აეროპორტი |
| `Airline` | ავიაკომპანია |
| `Flight` | ფრენა — საიდან, სად, დრო, ფასები |
| `Booking` | ჯავშანი — მომხმარებელი, ფრენა, კლასი, ჯამი, სტატუსი |
| `Passenger` | მგზავრი — სახელი, გვარი, პასპორტი, ადგილი |
| `Favorite` | შენახული ფრენა |

## გაშვება

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_flights   # სატესტო ფრენების შექმნა
python manage.py createsuperuser  # ადმინისთვის (არასავალდებულო)
python manage.py runserver
```

გახსენი: http://127.0.0.1:8000 · ადმინი: http://127.0.0.1:8000/admin

## ტესტები

```bash
python manage.py test
```

## სურათები

- ქალაქების ფოტოები — [Unsplash](https://unsplash.com)
- ბათუმი — [Batumi from the hill](https://commons.wikimedia.org/wiki/File:Batumi_from_the_hill.jpg), Wikimedia Commons
- თბილისი — [Bridge of Peace on River Mtkvari](https://commons.wikimedia.org/wiki/File:Bridge_of_Peace_on_River_Mtkvari.jpg), Wikimedia Commons
- ქუთაისი — [Rioni river](https://commons.wikimedia.org/wiki/File:2014_Kutaisi,_Rzeka_Rioni_obok_Mostu_Łańcuchowego_(01).jpg), Wikimedia Commons

## სტრუქტურა

```
skybook/      პროექტის პარამეტრები
accounts/     მომხმარებლები, რეგისტრაცია, ავტორიზაცია
flights/      ფრენები, ძიება, დაჯავშნა, პროფილი
templates/    HTML შაბლონები
static/       CSS და JavaScript
```
