from utils import Utils, ExcelWorker
from configparser import ConfigParser
import traceback

from components.LoggerWindow import Logger

class Executor:
    def __init__(self, logger: Logger, cache_path: str):
        self.utils = Utils(logger=logger, cache_path=cache_path)
        self.logger = logger
        self.urlParamMapping = {
            'до метро (мин)': {'urlParam': 'foot_min', 'filter': True},
            'площади': {'urlParam': '', 'filter': False},
        }
        self.repairMapping = {
            'дизайнерский': {'urlParam': 'repair%5B3%5D', 'value': '4', 'filter': False, 'label': 'Дизайнерский'},
            'евро': {'urlParam': 'repair%5B2%5D', 'value': '3', 'filter': False, 'label': 'Евро'},
            'косметический': {'urlParam': 'repair%5B1%5D', 'value': '2', 'filter': False, 'label': 'Косметический'},
            'без ремонта': {'urlParam': 'repair%5B0%5D', 'value': '1', 'filter': False, 'label': 'Без ремонта'},
        }
        self.districtsMapping = {
            'ИРКУТСК--РАЙОНЫ': {
                'ленинский': {'urlParam': 'district%5B0%5D', 'value': '958', 'filter': True, 'label': 'Ленинский'},
                'октябрьский': {'urlParam': 'district%5B1%5D', 'value': '961', 'filter': True, 'label': 'Октябрьский'},
                'правобережный': {'urlParam': 'district%5B2%5D', 'value': '960', 'filter': True, 'label': 'Правобережный'},
                'свердловский': {'urlParam': 'district%5B3%5D', 'value': '959', 'filter': True, 'label': 'Свердловский'},
            },
            'СОЧИ--РАЙОНЫ': {
                'адлерский': {'urlParam': 'district%5B0%5D', 'value': '157', 'filter': True, 'label': 'Адлерский'},
                'хостинский': {'urlParam': 'district%5B1%5D', 'value': '158', 'filter': True, 'label': 'Хостинский'},
                'центральный': {'urlParam': 'district%5B2%5D', 'value': '160', 'filter': True, 'label': 'Центральный'}
            },
            'КРАСНОДАР--РАЙОНЫ': {
                'западный': {'urlParam': 'district%5B0%5D', 'value': '565', 'filter': True, 'label': 'Западный'},
                'центральный': {'urlParam': 'district%5B1%5D', 'value': '566', 'filter': True, 'label': 'Центральный'},
                'карасунский': {'urlParam': 'district%5B2%5D', 'value': '567', 'filter': True, 'label': 'Карасунский'},
                'прикубанский': {'urlParam': 'district%5B3%5D', 'value': '564', 'filter': True, 'label': 'Прикубанский'}
            }
        }
        self.periodsMapping = {
            'oldCacheSection': 'выполнить запросы по старым домам',
            'middleCacheSection': 'выполнить запросы по средним домам',
            'newCacheSection': 'выполнить запросы по новым домам',
            'cacheSection': 'выполнить запросы по всем домам'
        }
        self.liftMapping = {
            'есть любой': {'urlParam': 'minlift', 'value': '1', 'filter': False, 'label': 'Любой'},
            'есть грузовой': {'urlParam': 'lift_service', 'value': '1', 'filter': False, 'label': 'Грузовой'},
        }
        self.ownerMapping = {
            'от собственника': {'urlParam': 'is_by_homeowner', 'value': '1', 'filter': False, 'label': 'От собственника'},
        }

    def getAreaUrlParams(self, isBuy):
        if isBuy:
            return {'min': 'mintarea', 'max': 'maxtarea'}
        return {'min': 'minarea', 'max': 'maxarea'}

    def filterOption(self, section, option):

        if section == None:
            return False

        simpleFilter = option.get('simpleFilter', None)
        if simpleFilter != None:
            return not simpleFilter

        toFilter = option.get('filter', False)
        if toFilter:
            if section.name == option['sectionName']:
                value = section.get(option['configPropertyName'], None)
                return value != None
            return False

        return True

    def isSectionEmpty(self, config, sectionName):
        result = True
        for key in config[sectionName].keys():
            if config[sectionName][key] == 'да':
                result = False
                break
        
        return result

    def getGroupLabel(self, config, sectionName):
        if self.isSectionEmpty(config, sectionName):
            return ''
        names = []
        for key in config[sectionName].keys():
            if config[sectionName][key] == 'да':
                if 'РЕМОНТ' in sectionName:
                    names.append(self.repairMapping[key]['label'])    
                elif 'РАЙОНЫ' in sectionName:
                    names.append(self.districtsMapping[sectionName][key]['label'])
                else:
                    names.append(self.urlParamMapping[key]['label'])
                
        
        return ', '.join(names)

    def getSelectedLift(self, config, sectionName):
        for key in config[sectionName].keys():
            if config[sectionName][key] == 'да':
                return key
        return ''

    def updateBundle(self, trace, urlParam, configPropertyName, groupId, value, decisions):
        index = next((i for i, item in enumerate(trace) if item.get('groupId', '') == groupId), -1)
        groupCopy = dict(trace[index])
        
        itemsCopy = []
        for i in range(len(groupCopy['extra'])):
            itemsCopy.append(dict(groupCopy['extra'][i]))

        copy = next((item for item in itemsCopy if item.get('urlParam', '') == urlParam), None)
        
        if value == 'да':           
            copy['value'] = decisions[configPropertyName]['value']
        else:
            copy['value'] = ''

        labels = []
        for item in itemsCopy:
            if item['value']:
                labels.append(item['label'])
            

        groupCopy['extra'] = itemsCopy
        groupCopy['label'] = ', '.join(labels)
        trace[index] = groupCopy

    def getOptions(self, config: ConfigParser, section, districtsSectionName, isBuy):
        commonSection = config['ОБЩИЕ']
        liftSectionName = 'ОБЩИЕ--ЛИФТ'
        repairSectionName = 'ОБЩИЕ--РЕМОНТ'
        ownerSectionName = 'ОБЩИЕ--СОБСТВЕННИК'

        multipleOptionMappings = list(filter(lambda option: self.filterOption(section, option), self.getMultipleOptionsMappings(config)))

        min_area, max_area = [commonSection['площади'].split('-')[0], commonSection['площади'].split('-')[1]] if '-' in commonSection['площади'] else ['', '']
        areaParams = self.getAreaUrlParams(isBuy)

        opts = []
        trace = list(filter(lambda opt: self.filterOption(section, opt), [
            {'id': ownerSectionName},
            {'id': liftSectionName},
            {'groupId': 'repair', 'label': '', 'extra': None},
            {'groupId': 'districts', 'label': '', 'extra': None, 'simpleFilter': not districtsSectionName},
            {'urlParam': areaParams['min'], 'value': min_area},
            {'urlParam': areaParams['max'], 'value': max_area},
            {'urlParam': 'min_house_year', 'value': '', 'hide': True},
            {'urlParam': 'max_house_year', 'value': '', 'hide': True},
            {
                'urlParam': 'foot_min', 
                'extra': [
                    {'urlParam': 'only_foot', 'value': '2'}
                ], 
                'value': section.get('до метро (мин)', ''), 'configPropertyName': 'до метро (мин)',
                'filter': True,
                'sectionName': section.name
            },
    
        ]))

        def rec(j):
            if j >= len(multipleOptionMappings):
                opts.append([] + trace)
                return

            urlParam = multipleOptionMappings[j]['urlParam']
            configPropertyName = multipleOptionMappings[j]['configPropertyName']
            sectionName = multipleOptionMappings[j]['sectionName']

            for i in range(len(multipleOptionMappings[j]['values'])):
                value = multipleOptionMappings[j]['values'][i]
                value = value if value != '""' else ''
                
                if configPropertyName == 'площади':
                    areas = value.split('-') if value else ['', '']
                    
                    area_min = areas[0]
                    area_max = areas[1]

                    index_min = next((i for i, item in enumerate(trace) if item.get('urlParam', '') == areaParams['min']), -1)
                    index_max = next((i for i, item in enumerate(trace) if item.get('urlParam', '') == areaParams['max']), -1)

                    copy_min = dict(trace[index_min])
                    copy_min['value'] = area_min
                    trace[index_min] = copy_min

                    copy_max = dict(trace[index_max])
                    copy_max['value'] = area_max
                    trace[index_max] = copy_max

                elif sectionName == repairSectionName:
                    self.updateBundle(trace, urlParam, configPropertyName, 'repair', value, self.repairMapping)

                elif sectionName == liftSectionName:
                    index = next((i for i, item in enumerate(trace) if item.get('id', '') == liftSectionName), -1)
                    copy = dict(trace[index])
                    copy['urlParam'] = value['urlParam']
                    copy['label'] = self.urlParamMapping[value['configPropertyName']]['label']
                    trace[index] = copy

                elif sectionName == districtsSectionName:
                    self.updateBundle(trace, urlParam, configPropertyName, 'districts', value, self.districtsMapping[districtsSectionName])

                else:
                    index = next((i for i, item in enumerate(trace) if item.get('urlParam', '') == urlParam), -1)
                    copy = dict(trace[index])
                    copy['value'] = value
                    trace[index] = copy
                    
                rec(j+1)

        rec(0)

        return opts

    def getOptimizations(self, isBuy, commonSection, typeSection):
        maxPricePropertyName = 'начальная средняя цена за квадратный метр' if isBuy else 'начальная средняя цена'
        maxPriceValue = typeSection[maxPricePropertyName]

        roundStep = commonSection['шаг поиска средней цены']

        common = [
            {
                'value': roundStep,
            }
        ]

        return [{
                    'urlParam': 'maxprice', 
                    'extra': [
                        {'urlParam': 'currency', 'value': '2'}, 
                        {'urlParam': 'm2', 'value': '1' if isBuy else ''}
                    ], 
                    'value': maxPriceValue
                },
        ] + common

    def getOptionsFragmentByCacheProperty(self, config, cacheProperty):
        commonSection = config['ОБЩИЕ']
        oldBound = commonSection['граница старых домов (год)']
        newBound = commonSection['граница новых домов (год)']
        optionsFragments = {
            'cacheSection': {'min_house_year': '', 'max_house_year': ''},
            'oldCacheSection': {'min_house_year': '', 'max_house_year': oldBound},
            'middleCacheSection': {'min_house_year': oldBound, 'max_house_year': newBound},
            'newCacheSection': {'min_house_year': newBound, 'max_house_year': ''}
        }
        return optionsFragments[cacheProperty]

    def getPeriodLabel(self, optionsFragment):
        minBound = optionsFragment['min_house_year']
        maxBound = optionsFragment['max_house_year']
        if minBound and maxBound:
            return f'{minBound} - {maxBound}'
        elif minBound:
            return f'от {minBound}'
        elif maxBound:
            return f'до {maxBound}'
        else:
            return f'весь период'
    

    def getMultipleOptionsMappings(self, config: ConfigParser):
        result = []
        for section in config.sections():
            if 'ЛИФТ' in section:
                pass
                # keys = [key for key in config[section].keys() if config[section][key] == 'да']
                # if len(keys) > 1:
                #     values = []
                #     for key in keys:
                #         values.append({'urlParam': urlParamMapping[key]['urlParam'], 'configPropertyName': key})
                #     result.append({'urlParam': 'lift', 'configPropertyName': 'lift', 'sectionName': section, 'values': values, 'filter': False})
            else:
                if 'РАЙОНЫ' in section:
                    urlParamMap = self.districtsMapping[section]
                elif 'РЕМОНТ' in section:
                    urlParamMap = self.repairMapping
                else:
                    urlParamMap = self.urlParamMapping
                for key in config[section].keys():
                    splitted = config[section][key].split(' ')
                    if len(splitted) > 1:
                        result.append({'urlParam': urlParamMap[key]['urlParam'], 'configPropertyName': key, 'values': splitted, 'filter': urlParamMap[key]['filter'], 'sectionName': section})
        return result

    def getDistrictsUrlMappings(self, config: ConfigParser, districtsSectionName):
        if not districtsSectionName:
            return [{'urlParam': '', 'value': '', 'label': ''}]
        else:
            extra = []
            for key in config[districtsSectionName].keys():
                if config[districtsSectionName][key] == 'да':
                    if key == 'неважно':
                        extra.append({'urlParam': '', 'value': '', 'label': 'Неважно'})
                    else:
                        options = self.districtsMapping[districtsSectionName][key]
                        extra.append({'urlParam': options['urlParam'], 'value': options['value'], 'label': options['label']})
            return extra
    
    def getRepairsUrlMappings(self, config: ConfigParser):
        repairSectionName = 'ОБЩИЕ--РЕМОНТ'
        extra = []
        for key in config[repairSectionName].keys():
            if config[repairSectionName][key] == 'да':
                if key == 'неважно':
                    extra.append({'urlParam': '', 'value': '', 'label': 'Неважно'})
                else:
                    options = self.repairMapping[key]
                    extra.append({'urlParam': options['urlParam'], 'value': options['value'], 'label': options['label']})
        
        return extra

    def getLiftUrlMappings(self, config: ConfigParser):
        liftSectionName = 'ОБЩИЕ--ЛИФТ'
        keys = []
        for key in config[liftSectionName].keys():
            if config[liftSectionName][key] == 'да':
                if key == 'неважно':
                    keys.append({'urlParam': '', 'value': '', 'label': 'Неважно'})
                else:
                    keys.append(dict(self.liftMapping[key]))
        
        return keys

    def getOwnerUrlMappings(self, config: ConfigParser):
        ownerSectionName = 'ОБЩИЕ--СОБСТВЕННИК'
        extra = []
        for key in config[ownerSectionName].keys():
            if config[ownerSectionName][key] == 'да':
                if key == 'неважно':
                    extra.append({'urlParam': '', 'value': '', 'label': 'Неважно'})
                else:
                    extra.append(dict(self.ownerMapping[key]))
        
        return extra

    def makeRow(self, config: ConfigParser, iterationObj, saleExcelWorker: ExcelWorker, rentExcelWorker: ExcelWorker):
        common = iterationObj['common']
        steps = iterationObj['steps']
        
        sectionName = common['cacheSection']
        section = config[sectionName]
        selectionSectionName = common['selectionSection']
        districtsSectionName = common.get('districtSection', None)
        periodSection = config['ОБЩИЕ--ПЕРИОДЫ']
        liftSectionName = 'ОБЩИЕ--ЛИФТ'
        ownerSectionName = 'ОБЩИЕ--СОБСТВЕННИК'
        sheetName = common['sheetName']

        for step in steps:
            url = step['url']
            fileName = step['fileName']
            stepType = step['type']
            isBuy = stepType == 'buy'
            toDo = config[selectionSectionName][step['select']] == 'да'
            if toDo:
                for options in self.getOptions(config, section, districtsSectionName, isBuy):
                    for district in self.getDistrictsUrlMappings(config, districtsSectionName):                    
                        if districtsSectionName:
                            districtOptionsGroup = next((opt for opt in options if opt.get('groupId', '') == 'districts'), -1)
                            districtOptionsGroup['extra'] = [district]
                            districtOptionsGroup['label'] = district['label']
                            
                        for repair in self.getRepairsUrlMappings(config):
                            repairOptionGroup = next((opt for opt in options if opt.get('groupId', '') == 'repair'), -1)
                            repairOptionGroup['extra'] = [repair]
                            repairOptionGroup['label'] = repair['label']

                            for lift in self.getLiftUrlMappings(config):
                                liftProperty = next((opt for opt in options if opt.get('id', '') == liftSectionName), -1)

                                liftProperty['urlParam'] = lift['urlParam']
                                liftProperty['value'] = lift['value']
                                liftProperty['label'] = lift['label']

                                for owner in self.getOwnerUrlMappings(config):
                                    ownerProperty = next((opt for opt in options if opt.get('id', '') == ownerSectionName), -1)

                                    ownerProperty['urlParam'] = owner['urlParam']
                                    ownerProperty['value'] = owner['value']
                                    ownerProperty['label'] = owner['label']

                                    if isBuy:
                                        saleExcelWorker.createRow(options, sheetName)
                                    else:
                                        rentExcelWorker.createRow(options, sheetName)

                                    for stepCacheProperty in ['oldCacheSection', 'middleCacheSection', 'newCacheSection', 'cacheSection']:
                                        if periodSection[self.periodsMapping[stepCacheProperty]] != 'да':
                                            if isBuy:
                                                saleExcelWorker.moveColumnsPointer(2)
                                            else:
                                                rentExcelWorker.moveColumnsPointer(2)
                                            continue

                                        cacheTypeSection = step[stepCacheProperty]
                                        typeSection = config[cacheTypeSection]
                                        commonSectionName = step['cacheSection']
                                        commonSection = config[commonSectionName]

                                        optionsFragment = self.getOptionsFragmentByCacheProperty(config, stepCacheProperty)
                                        
                                        min_house_year_option = next((item for item in options if item.get('urlParam', '') == 'min_house_year'), None)
                                        min_house_year_option['value'] = optionsFragment['min_house_year']
                                        max_house_year_option = next((item for item in options if item.get('urlParam', '') == 'max_house_year'), None)
                                        max_house_year_option['value'] = optionsFragment['max_house_year']

                                        optimizations = self.getOptimizations(isBuy, commonSection, typeSection)

                                        self.logger.println(f'\nВыполняется шаг для города: "{sheetName}" с Типом: "{fileName}". Период: "{self.getPeriodLabel(optionsFragment)}"')
                                        if districtsSectionName:
                                            self.logger.println(f'Район: {district["label"]}')
                                        self.logger.println(f'Ремонт: {repair["label"]}')
                                        self.logger.println(f'Лифт: {liftProperty["label"]}')
                                        self.logger.println(f'Собственник: {ownerProperty["label"]}')
                                        self.logger.println("")

                                        # self.logger.println(options)

                                        # REQUESTING AND SHOWING COUNT
                                        try:
                                            count = self.utils.getCountText(options, url)
                                            self.logger.println(count)

                                            # FINDING AND SHOWING THE AVG
                                            count = self.utils.retrieveCount(count) 
                                            self.logger.println('\nПоиск средней цены\n')

                                            missTuple = self.utils.getMissTuple(count, options, optimizations, url, isBuy)
                                            self.logger.println(f'Выявлена средняя цена: {missTuple[1]}\nС Погрешностью (Объявления): {missTuple[0]}\n')

                                            # SAVING AVG TO CACHE
                                            propertyName = 'начальная средняя цена за квадратный метр' if isBuy else 'начальная средняя цена'
                                            self.utils.saveToCache(config, cacheTypeSection, propertyName, missTuple[1])
                                            self.logger.println('Произведена запись в cache.ini\n')

                                            # APPENDING TO FILE
                                            if isBuy:
                                                saleExcelWorker.addToRow(count, missTuple[1])
                                            else:
                                                rentExcelWorker.addToRow(count, missTuple[1])
                                        
                                            self.logger.println('Обработчик завершил шаг!')
                                            self.logger.println(f'Город: "{sheetName}" Тип: "{fileName}" Период: "{self.getPeriodLabel(optionsFragment)}"')
                                        except:
                                            self.logger.println('Ошибка')
                                            traceback.print_exc()
                                            self.logger.println("")
                                            if isBuy:
                                                saleExcelWorker.moveColumnsPointer(2)
                                            else:
                                                rentExcelWorker.moveColumnsPointer(2)
