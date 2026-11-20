"""Paslaugų sluoksnis – baigiamojo darbo verslo logika.

Sluoksnis yra tarp maršrutų (routes/) ir duomenų modelių (models/), žr. aprašo
5 pav. „Sistemos architektūra“. Jį naudoja ir žiniatinklio procesas (web), ir
fono procesas (worker), todėl taisyklės vykdomos vienodai, nesvarbu, ar įvykį
sukėlė naudotojas, ar planuoklė.

Principai:
- maršrutų funkcijos tik priima užklausą, kviečia paslaugą ir parodo rezultatą;
- būsenų perėjimai, skaičiavimai ir pranešimų kūrimas aprašomi čia;
- paslaugos neatsako už HTTP (nenaudoja request, flash, redirect), todėl jas
  galima testuoti be naršyklės.
"""
