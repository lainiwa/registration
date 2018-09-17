
import Vue from 'vue';

import _ from 'lodash';
import axios from 'axios';
import alertify from 'alertifyjs';

import { base } from './index.js'

let app = new Vue({
    mixins: [base],
    el: '#app',

    data: {
        mode: 'typing',
        name: '',
        pred_names: [],
        letters: 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
    },

    computed: {
        // Список наличествующих имен. Без дубликатов, в верхнем регистре
        fullNameList() {
            return _.uniq(_.map(this.db['participants'],
                                participant => _.upperCase(participant.last_name)))
        },
        // Варианты возможных имен (учитывая уже вбитое имя)
        possibleNames() {
            return _.filter(this.fullNameList,
                            name => _.startsWith(_.upperCase(name), this.name))
        },
        // Какие буквы могут быть нажаты далее (учитывая уже вбитое имя и список возможных имен)
        possibleChars() {
            return _.map(this.possibleNames,
                         name => name.slice(this.name.length).charAt(0));
        },
        // Вбито ли имя полностью? Используется для активации кнопки `Далее`
        isNextEnabled() {
            return _.includes(this.possibleNames, this.name)
        },
        // Cписок однофамильцев для текущей фамилии
        allNamesakes() {
            return _.filter(this.db['participants'],
                            participant => _.upperCase(participant.last_name) === this.name)
        },
        // IP клиента, определенный сервером, на url с которым он нас (клиента) редиректнул
        // если только IP не был изначально определен в URL'е
        // в результате наш URL имеет вид http://<адрес_сервиса>:<порт_сервиса>/kiosk/<адрес_клиента_или_принтера>
        printerURL() {
            return new URL(document.URL).pathname.split('/').pop()
        }
    },

    methods: {
        // Может ли передаваемый `char` быть следующим в имени
        mightBeNext(char) {
            return _.includes(this.possibleChars, char)
        },
        // Возвращает строку, которую надо напечатать для различения однофамильцев
        formShortDescription(person) {
            return `${person.first_name} ${person.last_name} из команды "${person.team}"`
        },
        // Показывает попап, который потом исчезает. Используется для того, чтобы написать пользователю,
        // что его нельзя зарегистрировать, если он недавно уже зарегистрировался
        showNotification(text) {
            alertify.error('Вы уже зарагистрированы')
        },
        // Регистрирует переданного ей человека
        registerPerson(person) {
            let app = this
            app.api.post('check', person)
                .then(response => {
                    // console.log('Зарегано')
                    app.printTicket(person)
                })
                .catch(error => {
                    console.log(error.response.status)
                    if (error.response.status == 403) {
                        app.showNotification('Вы уже зарегистрировались')
                    }
                })
            app.name = ''
            app.mode = 'typing'
        },
        // Печатает чек человеку (передает соответствующему _локальному_ API post'ом json с информацией о человеке и его команде,
        // а также IP принтера, куда печатать)
        printTicket(person) {
            let app = this
            const team = _.filter(app.db.teams, team => team.name === person['team'])[0]
            app.api.post('print', {person: person, team: team, printer_ip: this.printerURL})
                .then(response => {
                    // console.log(response)
                })
                .catch(error => {
                    // console.log(error)
                })
        },
    },

    watch: {
        name(newValue, oldValue) {
            // Если очевидно, какая буква идет следующая, то добавляем ее к имени. Рекурсивно
            const next_chars = _.uniq(this.possibleChars)
            if (next_chars.length === 1) {
                this.name += next_chars[0]
            }
            // Если имя обнулили, то удаляем список предыдущих имен
            if (!this.name) {
                this.pred_names = []
            }
        },
    },
})
