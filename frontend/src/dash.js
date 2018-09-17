
import Vue from 'vue';
// если импортнуть после всего - то ломается axios xDDD
import Tabs from 'vue-tabs-component';
import VueGoodTablePlugin from 'vue-good-table';
import 'vue-good-table/dist/vue-good-table.css'

import moment from 'moment'
import 'moment/locale/ru';
import _ from 'lodash';
import axios from 'axios'; // axios и parcel не оч дружат вместе. иногда имеет значение порядок импорта аксиоса и остальных либ
import XLSX from 'xlsx'
import flatten from 'flat'
import * as Plotly from '../node_modules/plotly.js/dist/plotly.min.js'


import { base } from './index.js'


Vue.use(Tabs);
Vue.use(VueGoodTablePlugin);


let dash = new Vue({
    mixins: [base],
    el: '#dash',

    computed: {
        teamsWithParticipants() {
            // массив словарей вида
            // {team: <поля тимы>, participants: <массив словарей с полями участников>, calculated: <вычисленные из остальных поля>}
            return _.map(this.db.teams, team => {
                            let participants = _.filter(this.db.participants, participant => participant.team === team.name)
                            let joined = field => _.join(_.uniq(_.map(participants, p => p[field])), '; ')
                            let calculated = { schools: joined('school'), classnames: joined('classname') }
                            return { team: team, participants: participants, calculated: calculated}
                        })
        },
        allPairs() {
            // массив словарей вида {team: team, participant: participant}
            return _.map(this.db.participants,
                         participant => {
                            const team = _.filter(this.db.teams, team => team.name === participant['team'])[0]
                            return {participant: participant, team: team}
                        })
        },
        columnsParticipants() {
            return [
              { label: 'Команда',    field: 'team.name'  },
              { label: 'ID команды', field: 'team.tid'  },
              { label: 'Имя',        field: 'participant.first_name' },
              { label: 'Фамилия',    field: 'participant.last_name' },
              { label: 'Школа',      field: 'participant.school'  },
              { label: 'Класс',      field: 'participant.classname'  },
              { label: 'Время',      field: 'participant.time_checked', formatFn: this.humanizeISODate },
            ]
        },
        columnsTeams() {
            // высчитываем максимально возможное число участников на команду
            let maxMembersInTeam = Math.max.apply(null, _.map(this.teamsWithParticipants, row => row.participants.length))
            // к столбикам для описания команды "приклеиваем" столбики для описания учасников
            return _.reduce(
                Array.from({length: maxMembersInTeam}, (v, i) => i),
                (acc, i) => acc.concat([
                    { label: `Имя ${i+1}`,     field: `participants.${i}.first_name` },
                    { label: `Фамилия ${i+1}`, field: `participants.${i}.last_name` },
                    { label: `Время ${i+1}`,   field: `participants.${i}.time_checked`, formatFn: this.humanizeISODate },
                ]),
                [{ label: 'Команда',    field: 'team.name'},
                 { label: 'ID команды', field: 'team.tid' },
                 { label: 'Школы',      field: 'calculated.schools'   },
                 { label: 'Классы',     field: 'calculated.classnames'}]
            )
        },
    },

    methods: {
        humanizeISODate(isoDate) {
            // т.к. сервер отправляет время с GMT+0, а мы находимся в мск (GMT+3),
            // то выравниваем это дело
            let curr_offset = moment(new Date()).utcOffset() // 180 (в минутах)
            let real_date = moment(new Date(isoDate)).subtract(curr_offset, 'minutes')
            return isoDate ? real_date.format('MMMM Do, h:mm:ss a') : ''
        },
        perticipantsRowClass(row) {
            return row.participant.time_checked ? 'green-row' : 'red-row'
        },
        teamsRowClass(row) {
            let times = _.map(row.participants, p => p.time_checked)
            return times.every(_.identity)
                   ? 'green-row'
                   : times.some(_.identity)
                     ? 'yellow-row'
                     : 'red-row'
        },
        plotGraph() {
            const by_team = _.groupBy(this.db.participants, 'team')
            const teams = Object.keys(by_team)
            const fullness = _.map(by_team, lst => _.filter(lst, 'time_checked').length / lst.length)
            const data = [{
                x: teams,
                y: fullness,
                type: 'bar',
            }]
            const layout = {
                yaxis: {range: [0, 1]}
            }
            Plotly.newPlot('myDiv', data, layout)
        },
        downloadXLSX() {
            let wb = XLSX.utils.book_new()
            // таблица участников
            let ws = XLSX.utils.table_to_sheet(document.querySelector('#table-members table'))
            XLSX.utils.book_append_sheet(wb, ws, 'участники')
            // таблица команд
            ws = XLSX.utils.table_to_sheet(document.querySelector('#table-teams table'))
            XLSX.utils.book_append_sheet(wb, ws, 'команды')
            // дамп по участникам
            let data = _.map(this.allPairs, flatten)
            ws = XLSX.utils.json_to_sheet(data)
            XLSX.utils.book_append_sheet(wb, ws, 'участники_дамп');
            // дамп по командам
            data = _.map(this.teamsWithParticipants, flatten)
            ws = XLSX.utils.json_to_sheet(data)
            XLSX.utils.book_append_sheet(wb, ws, 'команды_дамп');
            /* генерируем файл и кидаемся им в пользователя */
            XLSX.writeFile(wb, 'таблица_участников.xlsx');
        },
    },

    watch: {
        db(newValue, oldValue) {
            this.plotGraph()
        },
    },

})
