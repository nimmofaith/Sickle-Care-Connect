#!/usr/bin/env python3
"""
seed_doctors.py - Populate initial hospital and doctor data for Kenyan hospitals

Run this script to create sample hospitals and doctors for testing:
    python seed_doctors.py
"""

from app import app, db
from models import Hospital, Doctor
from werkzeug.security import generate_password_hash


def seed_data():
    """Create initial hospitals and doctors"""
    with app.app_context():
        # Create hospitals (from findcare2.html - Kenyan hospitals)
        hospitals_data = [
            {
                "name": "Nakuru County Referral & Teaching Hospital",
                "address": "Along Hospital Road, near Nyayo Gardens",
                "phone": "+254-20-2030000",
                "city": "Nakuru",
                "state": "Rift Valley"
            },
            {
                "name": "Mediheal Hospital Nakuru",
                "address": "Kenyatta Avenue, opposite Westside Mall",
                "phone": "+254-51-2066666",
                "city": "Nakuru",
                "state": "Rift Valley"
            },
            {
                "name": "Naivasha County Referral Hospital",
                "address": "Moi South Lake Road, near Naivasha Stadium",
                "phone": "+254-50-2030000",
                "city": "Nakuru",
                "state": "Rift Valley"
            },
            {
                "name": "Rhein-Valley Hospital",
                "address": "Pipeline area, off Nairobi–Nakuru Highway",
                "phone": "+254-51-2400000",
                "city": "Nakuru",
                "state": "Rift Valley"
            },
            {
                "name": "St. Mary's Mission Hospital Gilgil",
                "address": "Gilgil town, along Nairobi–Nakuru Highway",
                "phone": "+254-50-2033333",
                "city": "Nakuru",
                "state": "Rift Valley"
            },
            {
                "name": "Aga Khan University Hospital",
                "address": "3rd Parklands Avenue, near Diamond Plaza",
                "phone": "+254-20-3662000",
                "city": "Nairobi",
                "state": "Nairobi"
            },
            {
                "name": "Comprehensive Sickle Cell Management Center",
                "address": "Eastleigh, near Pumwani Maternity Hospital",
                "phone": "+254-20-3672000",
                "city": "Nairobi",
                "state": "Nairobi"
            },
            {
                "name": "Mbagathi County Referral Hospital",
                "address": "Mbagathi Way, next to Kenyatta Market",
                "phone": "+254-20-2700000",
                "city": "Nairobi",
                "state": "Nairobi"
            }
        ]

        hospitals = []
        for hosp_data in hospitals_data:
            existing = Hospital.query.filter_by(name=hosp_data["name"]).first()
            if not existing:
                hospital = Hospital(**hosp_data)
                db.session.add(hospital)
                hospitals.append(hospital)
            else:
                hospitals.append(existing)

        db.session.commit()

        # Create doctors (all are sickle cell doctors)
        # One doctor per hospital
        doctors_data = [
            {
                "email": "dr.karen.wanja@nakuru.com",
                "password": generate_password_hash("password123"),
                "first_name": "Karen",
                "last_name": "Wanja",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001234",
                "phone": "+254712345678",
                "hospital_id": hospitals[0].id
            },
            {
                "email": "dr.janice.njeri@nakuru.com",
                "password": generate_password_hash("password123"),
                "first_name": "Janice",
                "last_name": "Njeri",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001235",
                "phone": "+254723456789",
                "hospital_id": hospitals[1].id
            },
            {
                "email": "dr.patricia.ombuya@nakuru.com",
                "password": generate_password_hash("password123"),
                "first_name": "Patricia",
                "last_name": "Ombuya",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001236",
                "phone": "+254734567890",
                "hospital_id": hospitals[2].id
            },
            {
                "email": "dr.simon.okelo@nakuru.com",
                "password": generate_password_hash("password123"),
                "first_name": "Simon",
                "last_name": "Okelo",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001237",
                "phone": "+254745678901",
                "hospital_id": hospitals[3].id
            },
            {
                "email": "dr.kate.maina@nakuru.com",
                "password": generate_password_hash("password123"),
                "first_name": "Kate",
                "last_name": "Maina",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001238",
                "phone": "+254756789012",
                "hospital_id": hospitals[4].id
            },
            {
                "email": "dr.patel.shiv@nairobi.com",
                "password": generate_password_hash("password123"),
                "first_name": "Patel",
                "last_name": "Shiv",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001239",
                "phone": "+254767890123",
                "hospital_id": hospitals[5].id
            },
            {
                "email": "dr.michael.njoroge@nairobi.com",
                "password": generate_password_hash("password123"),
                "first_name": "Michael",
                "last_name": "Njoroge",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001240",
                "phone": "+254778901234",
                "hospital_id": hospitals[6].id
            },
            {
                "email": "dr.alice.mbatia@nairobi.com",
                "password": generate_password_hash("password123"),
                "first_name": "Alice",
                "last_name": "Mbatia",
                "specialization": "Sickle Cell Doctor",
                "license_number": "MD001241",
                "phone": "+254789012345",
                "hospital_id": hospitals[7].id
            }
        ]

        for doc_data in doctors_data:
            existing = Doctor.query.filter_by(email=doc_data["email"]).first()
            if not existing:
                doctor = Doctor(**doc_data)
                db.session.add(doctor)
                print(
                    f"✓ Created doctor: {doc_data['first_name']} {doc_data['last_name']}")
            else:
                print(f"~ Doctor already exists: {doc_data['email']}")

        db.session.commit()
        print("\n✓ Seed data created successfully!")
        print("\nTest Login Credentials:")
        print("=" * 50)
        for doc_data in doctors_data:
            print(f"Email: {doc_data['email']}")
            print(f"Password: password123")
            print(
                f"Hospital: {hospitals[doctors_data.index(doc_data)].name}\n")


if __name__ == "__main__":
    seed_data()
