package com.example.model.entity;

import jakarta.persistence.*;

/*
Please refer resources/schema.sql for the table structure.
The entity represents the data model of the Bank Customers table. It maps to a database table & columns.
*/

@Entity
@Table(name = "BANK_CUSTOMERS")

public class Customer {

    @Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;
    
    @Column(name = "CUSTOMER_NAME")
    private String customerName;

    @Column(name = "GENDER")
    private String gender;          

    @Column(name = "MARITAL_STATUS")
    private String maritalStatus;

    @Column(name = "STREET_ADDRESS")
    private String streetAddress;

    @Column(name = "CITY")
    private String city;

    @Column(name = "STATE")
    private String state;

    @Column(name = "PHONE_NUMBER")
    private String phoneNumber;

    @Column(name = "EMAIL")
    private String email;

    public Customer() {
    }   

    public Customer(String customerName, String gender, String maritalStatus, String streetAddress, String city,
            String state, String phoneNumber, String email) {
        this.customerName = customerName;       
        this.gender = gender;
        this.maritalStatus = maritalStatus;
        this.streetAddress = streetAddress;
        this.city = city;
        this.state = state;
        this.phoneNumber = phoneNumber;
        this.email = email;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public String getMaritalStatus() {
        return maritalStatus;
    }

    public void setMaritalStatus(String maritalStatus) {
        this.maritalStatus = maritalStatus;
    }

    public String getStreetAddress() {
        return streetAddress;
    }

    public void setStreetAddress(String streetAddress) {
        this.streetAddress = streetAddress;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public String getPhoneNumber() {
        return phoneNumber;
    }

    public void setPhoneNumber(String phoneNumber) {
        this.phoneNumber = phoneNumber;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    
    
}

