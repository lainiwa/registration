import Vue from 'vue';

import _ from 'lodash';
import axios from 'axios';


export const base = {
    // Данные:
    //   * дамп данных из БД со структурой {'teams': [...], 'participants': [...]},
    //     где списки содержат строки соответсвующих таблиц
    //   * строка с датой последних изменений в БД
    //   * ... и в файлах сайта
    data: {
        db: {},
        db_last_changed: '',
        files_last_changed: '',
        api: axios.create({
                baseURL: '/api/',
                auth: {
                    username: process.env.API_LOGIN,
                    password: process.env.API_PASSWORD,
                },
            }),
    },

    // Обновляем даты последних изменений в БД и в файлах каждые 5 секунд.
    // В случае изменений в БД - скачиваем все данные из БД заново.
    // В случае перегенерирования файлов фронтенда - перезагружаем страницу.
    mounted() {
        let app = this
        app.requestDBLastChanged(app)
        setInterval(app.requestDBLastChanged, 5000)
        setInterval(app.requestFilesLastChanged, 5000)
    },

    methods: {
        // Скачивает все данные из БД в переменную `db`.
        requestFullDB() {
            let app = this
            app.api.get('db')
                .then(response => {
                    app.db = response.data
                    console.log(app.db)
                    console.log(app.fullNameList)
                })
                .catch(error => {
                    // tsss...
                })
        },
        // Записать в `db_last_changed` строку с датой последних изменений в БД
        requestDBLastChanged() {
            let app = this
            app.api.post('db')
                .then(response => {
                    app.db_last_changed = response.data['last_changed']
                })
                .catch(error => {
                    // tsss...
                })
        },
        //
        // Записать в `files_last_changed` строку с датой последних изменений в папке со статикой
        requestFilesLastChanged() {
            let app = this
            app.api.post('files')
                .then(response => {
                    app.files_last_changed = response.data['last_changed']
                })
                .catch(error => {
                    // tsss...
                })
        },
    },

    watch: {
        // Если в БД есть какие-то изменения - скачиваем из нее все данные заново
        db_last_changed(newValue, oldValue) {
            this.requestFullDB()
        },
        // Если какой-то статический контент изменился - обновляем страницу (за исключением первого раза)
        files_last_changed(newValue, oldValue) {
            if (oldValue) {
                location.reload()
            }
        },
    },
}
