# encoding: UTF-8

'''
vnpy.api.okex的gateway接入

Contributor：ipqhjjybj 大佳
'''
from __future__ import print_function

import time
import os
import json
from datetime import datetime
from time import sleep
from copy import copy
from threading import Condition
from queue import Queue, Empty
from threading import Thread
from time import sleep

from vnpy.api.okex import OkexSpotApi, OkexFuturesApi, OKEX_SPOT_HOST, OKEX_FUTURES_HOST

from vnpy.trader.vtGateway import *
from vnpy.trader.vtFunction import getJsonPath

# 价格类型映射
# 买卖类型： 限价单（buy/sell） 市价单（buy_market/sell_market）
priceTypeMap = {}
futurepriceTypeMap = {}
priceTypeMap['buy'] = (DIRECTION_LONG, PRICETYPE_LIMITPRICE)
priceTypeMap['buy_market'] = (DIRECTION_LONG, PRICETYPE_MARKETPRICE)
priceTypeMap['sell'] = (DIRECTION_SHORT, PRICETYPE_LIMITPRICE)
priceTypeMap['sell_market'] = (DIRECTION_SHORT, PRICETYPE_MARKETPRICE)  ###原版现货下单映射

futurepriceTypeMap['1'] = (DIRECTION_LONG,OFFSET_OPEN)               ##买开
futurepriceTypeMap['2'] = (DIRECTION_SHORT,OFFSET_OPEN)             ##卖开
futurepriceTypeMap['3'] = (DIRECTION_SHORT,OFFSET_CLOSE)              #卖平  
futurepriceTypeMap['4'] = (DIRECTION_LONG,OFFSET_CLOSE)               #买平
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 
futurepriceTypeMapReverse = {v: k for k, v in futurepriceTypeMap.items()} 

# 委托状态印射
statusMap = {}
statusMap[-1] = STATUS_CANCELLED
statusMap[0] = STATUS_NOTTRADED
statusMap[1] = STATUS_PARTTRADED
statusMap[2] = STATUS_ALLTRADED
statusMap[4] = STATUS_UNKNOWN

okex_all_symbol_pairs = ['ref_usdt', 'soc_usdt', 'light_usdt', 'avt_usdt', 
'of_usdt', 'brd_usdt', 'ast_usdt', 'int_usdt', 'zrx_usdt', 'ctr_usdt', 'dgd_usdt', 
'aidoc_usdt', 'wtc_usdt', 'swftc_usdt', 'wrc_usdt', 'sub_usdt', 'dna_usdt', 'knc_usdt', 
'kcash_usdt', 'mdt_usdt', 'theta_usdt', 'ppt_usdt', 'utk_usdt', 'qvt_usdt', 'salt_usdt', 
'la_usdt', 'itc_usdt', 'fair_usdt', 'yee_usdt', '1st_usdt', 'fun_usdt', 'iost_usdt', 'mkr_usdt', 
'tio_usdt', 'req_usdt', 'ubtc_usdt', 'icx_usdt', 'tct_usdt', 'san_usdt', 'lrc_usdt', 'icn_usdt', 
'cvc_usdt', 'eth_usdt', 'poe_usdt', 'xlm_usdt', 'iota_usdt', 'eos_usdt', 'nuls_usdt', 'mot_usdt', 
'neo_usdt', 'gnx_usdt', 'dgb_usdt', 'evx_usdt', 'ltc_usdt', 'mda_usdt', 'etc_usdt', 'dpy_usdt', 
'tnb_usdt', 'nas_usdt', 'btc_usdt', 'smt_usdt', 'ssc_usdt', 'oax_usdt', 'yoyo_usdt', 'snc_usdt', 
'sngls_usdt', 'bch_usdt', 'mana_usdt', 'mof_usdt', 'mco_usdt', 'vib_usdt', 'topc_usdt', 'pra_usdt', 
'bnt_usdt', 'xmr_usdt', 'edo_usdt', 'snt_usdt', 'eng_usdt', 'stc_usdt', 'qtum_usdt', 'key_usdt', 
'ins_usdt', 'rnt_usdt', 'bcd_usdt', 'amm_usdt', 'lend_usdt', 'btm_usdt', 'elf_usdt', 'xuc_usdt', 
'cag_usdt', 'snm_usdt', 'act_usdt', 'dash_usdt', 'zec_usdt', 'storj_usdt', 'pay_usdt', 'vee_usdt', 
'show_usdt', 'trx_usdt', 'atl_usdt', 'ark_usdt', 'ost_usdt', 'gnt_usdt', 'dat_usdt', 'rcn_usdt', 
'qun_usdt', 'mth_usdt', 'rct_usdt', 'read_usdt', 'gas_usdt', 'btg_usdt', 'mtl_usdt', 'cmt_usdt', 
'xrp_usdt', 'spf_usdt', 'aac_usdt', 'can_usdt', 'omg_usdt', 'hsr_usdt', 'link_usdt', 'dnt_usdt', 
'true_usdt', 'ukg_usdt', 'xem_usdt', 'ngc_usdt', 'lev_usdt', 'rdn_usdt', 'ace_usdt', 'ipc_usdt', 
'ugc_usdt', 'viu_usdt', 'mag_usdt', 'hot_usdt', 'pst_usdt','ref_btc', 'soc_btc', 'light_btc', 
'avt_btc', 'of_btc', 'brd_btc', 'ast_btc', 'int_btc', 'zrx_btc', 'ctr_btc', 'dgd_btc', 'aidoc_btc', 
'wtc_btc', 'swftc_btc', 'wrc_btc', 'sub_btc', 'dna_btc', 'knc_btc', 'kcash_btc', 'mdt_btc', 
'theta_btc', 'ppt_btc', 'utk_btc', 'qvt_btc', 'salt_btc', 'la_btc', 'itc_btc', 'fair_btc', 
'yee_btc', '1st_btc', 'fun_btc', 'iost_btc', 'mkr_btc', 'tio_btc', 'req_btc', 'ubtc_btc', 
'icx_btc', 'tct_btc', 'san_btc', 'lrc_btc', 'icn_btc', 'cvc_btc', 'eth_btc', 'poe_btc', 'xlm_btc', 
'iota_btc', 'eos_btc', 'nuls_btc', 'mot_btc', 'neo_btc', 'gnx_btc', 'dgb_btc', 'evx_btc', 
'ltc_btc', 'mda_btc', 'etc_btc', 'dpy_btc', 'tnb_btc', 'nas_btc', 'btc_btc', 'smt_btc', 'ssc_btc', 
'oax_btc', 'yoyo_btc', 'snc_btc', 'sngls_btc', 'bch_btc', 'mana_btc', 'mof_btc', 'mco_btc', 
'vib_btc', 'topc_btc', 'pra_btc', 'bnt_btc', 'xmr_btc', 'edo_btc', 'snt_btc', 'eng_btc', 'stc_btc', 
'qtum_btc', 'key_btc', 'ins_btc', 'rnt_btc', 'bcd_btc', 'amm_btc', 'lend_btc', 'btm_btc', 
'elf_btc', 'xuc_btc', 'cag_btc', 'snm_btc', 'act_btc', 'dash_btc', 'zec_btc', 'storj_btc', 
'pay_btc', 'vee_btc', 'show_btc', 'trx_btc', 'atl_btc', 'ark_btc', 'ost_btc', 'gnt_btc', 
'dat_btc', 'rcn_btc', 'qun_btc', 'mth_btc', 'rct_btc', 'read_btc', 'gas_btc', 'btg_btc', 
'mtl_btc', 'cmt_btc', 'xrp_btc', 'spf_btc', 'aac_btc', 'can_btc', 'omg_btc', 'hsr_btc', 
'link_btc', 'dnt_btc', 'true_btc', 'ukg_btc', 'xem_btc', 'ngc_btc', 'lev_btc', 'rdn_btc', 
'ace_btc', 'ipc_btc', 'ugc_btc', 'viu_btc', 'mag_btc', 'hot_btc', 'pst_btc']

########################################################################
class OkexGateway(VtGateway):
    """OKEX交易接口"""
    
    #----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='OKEX'):
        """Constructor"""
        super(OkexGateway, self).__init__(eventEngine, gatewayName)
        
        self.spotApi = SpotApi(self)     
        self.futuresApi = FuturesApi(self)
        
        self.leverage = 0
        self.connected = False
        self.fileName = self.gatewayName + '_connect.json'
        self.filePath = getJsonPath(self.fileName, __file__)     

    #----------------------------------------------------------------------
    def connect(self):
        """连接"""
        # 载入json文件
        try:
            f = open(self.filePath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取连接配置出错，请检查'
            self.onLog(log)
            return
        
        # 解析json文件
        setting = json.load(f)
        try:
            apiKey = str(setting['apiKey'])
            secretKey = str(setting['secretKey'])
            trace = setting['trace']
            symbols = setting['symbols']
            contracts = setting['contracts']

        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return            
        
        # 初始化接口
        # self.spotApi.init(apiKey, secretKey, trace, symbols)
        self.futuresApi.init(apiKey, secretKey, trace, contracts)


    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""

        pass
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        # if len(orderReq.contractType)<4:
        #     return self.spotApi.sendOrder(orderReq)
        # else:
        #     return self.futuresApi.sendOrder(orderReq)
        return self.futuresApi.sendOrder(orderReq)
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        # if len(cancelOrderReq.contractType) < 4:
        #     return self.spotApi.cancelOrder(cancelOrderReq)   
        # else:
        #     return self.futuresApi.cancelOrder(cancelOrderReq)     
        return self.futuresApi.cancelOrder(cancelOrderReq) 
    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户资金"""

        pass

    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        # self.futuresApi.futuresUserInfo()
        pass
    #------------------------------------------------
    def loadHistoryBars(self):
        """策略初始化时下载历史数据"""
        pass

    #------------------------------------------------
    def initPosition(self,vtSymbol):
        """策略初始化时查询策略的持仓"""
        symbol = vtSymbol[:3]
        contractType = vtSymbol[4:-5]
        if len(contractType) > 4:
            self.futuresApi.rest_futures_position(symbol,contractType)
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.futuresApi.close()
        self.spotApi.close()
        
    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryPosition]
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 2         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()  
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
                
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled


##################################################################################################
class SpotApi(OkexSpotApi):
    """OKEX的现货SPOTAPI实现"""

    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(SpotApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称

        self.cbDict = {}
        self.tickDict = {}
        
        self.channelSymbolMap = {}

        # 为了期货和现货共存于这个gateway，将两个类的委托号移到此处共享
        self.orderDict = {}
        self.localNo = 0                # 本地委托号
        self.localNoQueue = Queue()     # 未收到系统委托号的本地委托号队列
        self.localNoDict = {}           # key为本地委托号，value为系统委托号
        self.localOrderDict = {}        # key为本地委托号, value为委托对象
        self.orderIdDict = {}           # key为系统委托号，value为本地委托号
        self.cancelDict = {}            # key为本地委托号，value为撤单请求

        self.recordOrderId_BefVolume = {}       # 记录的之前处理的量

        self.cache_some_order = {}
        self.tradeID = 0

        self.registerSymbolPairArray = set([])

    #----------------------------------------------------------------------
    def onMessage(self, data):
        """信息推送""" 
        channel = data.get('channel', '')
        if not channel:
            return

        if channel in self.cbDict:
            callback = self.cbDict[channel]
            callback(data)

    #----------------------------------------------------------------------
    def onError(self, data):
        """错误推送"""
        error = VtErrorData()
        error.gatewayName = self.gatewayName
        error.errorMsg = str(data)
        self.gateway.onError(error)
        
    #----------------------------------------------------------------------
    def onClose(self):
        """接口断开"""
        self.gateway.connected = False
        self.writeLog(u'现货服务器连接断开')
    
    #----------------------------------------------------------------------
    def onOpen(self):       
        """连接成功"""
        self.gateway.connected = True
        self.writeLog(u'现货服务器连接成功')
        
        self.login()
        
        # 推送合约数据
        for symbol in self.symbols:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName
            contract.symbol = symbol
            contract.exchange = self.gatewayName
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            contract.name = symbol
            
            contract.size = 0.00001
            contract.priceTick = 0.00001
            contract.productClass = PRODUCT_SPOT
            self.gateway.onContract(contract)
    
    #----------------------------------------------------------------------
    def initCallback(self):
        """初始化回调函数"""
        for symbol in self.symbols:
            # channel和symbol映射
            self.channelSymbolMap["ok_sub_spot_%s_ticker" % symbol] = symbol
            self.channelSymbolMap["ok_sub_spot_%s_depth_10" % symbol] = symbol
            self.channelSymbolMap["ok_sub_spot_%s_deals" % symbol] = symbol
            
            # channel和callback映射
            self.cbDict["ok_sub_spot_%s_ticker" % symbol] = self.onTicker
            self.cbDict["ok_sub_spot_%s_depth_10" % symbol] = self.onDepth
            self.cbDict["ok_sub_spot_%s_deals" % symbol] = self.onDeals
            self.cbDict["ok_sub_spot_%s_order" % symbol] = self.onSubSpotOrder
            self.cbDict["ok_sub_spot_%s_balance" % symbol] = self.onSubSpotBalance

        self.cbDict['ok_spot_userinfo'] = self.onSpotUserInfo
        self.cbDict['ok_spot_orderinfo'] = self.onSpotOrderInfo
        self.cbDict['ok_spot_order'] = self.onSpotOrder
        self.cbDict['ok_spot_cancel_order'] = self.onSpotCancelOrder
        self.cbDict['login'] = self.onLogin
    
    #----------------------------------------------------------------------
    def onLogin(self, data):
        """"""
        # 查询持仓
        self.spotUserInfo()
        
        # 订阅推送
    
        for symbol in self.symbols:
            self.subscribe(symbol)
        self.writeLog(u'现货服务器登录成功')
    #----------------------------------------------------------------------
    def onTicker(self, data):
        """"""
        channel = data['channel']
        symbol = self.channelSymbolMap[channel]
        
        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            tick.gatewayName = self.gatewayName
            
            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        d = data['data']
        tick.highPrice = float(d['high'])
        tick.lowPrice = float(d['low'])
        tick.lastPrice = float(d['last'])
        tick.volume = float(d['vol'].replace(',', ''))
        tick.date, tick.time = self.generateDateTime(d['timestamp'])
        tick.volumeChange = 0
        tick.localTime = datetime.now()
        if tick.bidPrice1 and tick.lastVolume:
            newtick = copy(tick)
            self.gateway.onTick(newtick)
    
    #----------------------------------------------------------------------
    def onDepth(self, data):
        """"""
        channel = data['channel']
        symbol = self.channelSymbolMap[channel]

        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            tick.gatewayName = self.gatewayName

            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        d = data['data']
        
        tick.bidPrice1, tick.bidVolume1 = d['bids'][0]
        tick.bidPrice2, tick.bidVolume2 = d['bids'][1]
        tick.bidPrice3, tick.bidVolume3 = d['bids'][2]
        tick.bidPrice4, tick.bidVolume4 = d['bids'][3]
        tick.bidPrice5, tick.bidVolume5 = d['bids'][4]
        tick.bidPrice6, tick.bidVolume6 = d['bids'][5]
        tick.bidPrice7, tick.bidVolume7 = d['bids'][6]
        tick.bidPrice8, tick.bidVolume8 = d['bids'][7]
        tick.bidPrice9, tick.bidVolume9 = d['bids'][8]
        tick.bidPrice10, tick.bidVolume10 = d['bids'][9]
        
        tick.askPrice1, tick.askVolume1 = d['asks'][-1]
        tick.askPrice2, tick.askVolume2 = d['asks'][-2]
        tick.askPrice3, tick.askVolume3 = d['asks'][-3]
        tick.askPrice4, tick.askVolume4 = d['asks'][-4]
        tick.askPrice5, tick.askVolume5 = d['asks'][-5]   
        tick.askPrice6, tick.askVolume6 = d['asks'][-6]
        tick.askPrice7, tick.askVolume7 = d['asks'][-7]
        tick.askPrice8, tick.askVolume8 = d['asks'][-8]
        tick.askPrice9, tick.askVolume9 = d['asks'][-9]
        tick.askPrice10, tick.askVolume10 = d['asks'][-10]  
        
        tick.bidPrice1 = float(tick.bidPrice1)
        tick.bidPrice2 = float(tick.bidPrice2)
        tick.bidPrice3 = float(tick.bidPrice3)
        tick.bidPrice4 = float(tick.bidPrice4)
        tick.bidPrice5 = float(tick.bidPrice5)
        tick.askPrice1 = float(tick.askPrice1)
        tick.askPrice2 = float(tick.askPrice2)
        tick.askPrice3 = float(tick.askPrice3)
        tick.askPrice4 = float(tick.askPrice4)
        tick.askPrice5 = float(tick.askPrice5)   
        
        tick.bidVolume1 = float(tick.bidVolume1)
        tick.bidVolume2 = float(tick.bidVolume2)
        tick.bidVolume3 = float(tick.bidVolume3)
        tick.bidVolume4 = float(tick.bidVolume4)
        tick.bidVolume5 = float(tick.bidVolume5)
        tick.askVolume1 = float(tick.askVolume1)
        tick.askVolume2 = float(tick.askVolume2)
        tick.askVolume3 = float(tick.askVolume3)
        tick.askVolume4 = float(tick.askVolume4)
        tick.askVolume5 = float(tick.askVolume5)          

        tick.bidPrice6 = float(tick.bidPrice6)
        tick.bidPrice7 = float(tick.bidPrice7)
        tick.bidPrice8 = float(tick.bidPrice8)
        tick.bidPrice9 = float(tick.bidPrice9)
        tick.bidPrice10 = float(tick.bidPrice10)
        tick.askPrice6 = float(tick.askPrice6)
        tick.askPrice7 = float(tick.askPrice7)
        tick.askPrice8 = float(tick.askPrice8)
        tick.askPrice9 = float(tick.askPrice9)
        tick.askPrice10 = float(tick.askPrice10)   
        
        tick.bidVolume6 = float(tick.bidVolume6)
        tick.bidVolume7 = float(tick.bidVolume7)
        tick.bidVolume8 = float(tick.bidVolume8)
        tick.bidVolume9 = float(tick.bidVolume9)
        tick.bidVolume10 = float(tick.bidVolume10)
        tick.askVolume6 = float(tick.askVolume6)
        tick.askVolume7 = float(tick.askVolume7)
        tick.askVolume8 = float(tick.askVolume8)
        tick.askVolume9 = float(tick.askVolume9)
        tick.askVolume10 = float(tick.askVolume10)          
        
        tick.date, tick.time = self.generateDateTime(d['timestamp'])
        tick.volumeChange  = 0
        tick.localTime = datetime.now()
        if tick.lastPrice and tick.lastVolume:
            newtick = copy(tick)
            self.gateway.onTick(newtick)

    def onDeals(self,data):
        """获取TICK成交量
        [{"channel":"ok_sub_spot_bch_btc_deals","data":[["1001","2463.86","0.052","16:34:07","ask"]]}]
        """
        channel = data['channel']
        symbol = self.channelSymbolMap[channel]

        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            tick.gatewayName = self.gatewayName

            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        for i in range(len(data['data'])):
            d = data['data'][i]
            tick.lastPrice = float(d[1])
            tick.lastVolume = float(d[2])
            tick.time = d[3]+".000000"
            tick.type = d[4]
            tick.volumeChange = 1
            tick.localTime = datetime.now()
            
            if tick.bidPrice1:
                newtick = copy(tick)
                self.gateway.onTick(newtick)
    
    #----------------------------------------------------------------------        
    def onSpotOrder(self, data):
        """"""
        # 如果委托失败，则通知委托被拒单的信息
        if self.checkDataError(data):
            try:
                localNo = self.localNoQueue.get_nowait()
            except Empty:
                return
            
            order = self.localOrderDict[localNo]
            order.status = STATUS_REJECTED
            self.gateway.onOrder(order)
    
    #----------------------------------------------------------------------
    def onSpotCancelOrder(self, data):
        """"""
        self.checkDataError(data)
        
    #----------------------------------------------------------------------
    def onSpotUserInfo(self, data):
        """现货账户资金推送"""
        if self.checkDataError(data):
            return
        
        funds = data['data']['info']['funds']
        free = funds['free']
        freezed = funds['freezed']
        # 持仓信息
        for symbol in free.keys():
            frozen = float(freezed[symbol])
            available = float(free[symbol])
            
            if frozen or available:
                pos = VtPositionData()
                pos.gatewayName = self.gatewayName
                
                pos.symbol = symbol
                pos.exchange = self.gatewayName
                pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
                pos.direction = DIRECTION_LONG
                pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])
                
                pos.frozen = frozen
                pos.position = frozen + available
                    
                self.gateway.onPosition(pos)
        
        self.writeLog(u'现货持仓信息查询成功')
        
        # 查询委托
        # for symbol in self.symbols:
        #     self.spotOrderInfo(symbol, '-1')        
            
    #----------------------------------------------------------------------
    def onSpotOrderInfo(self, data):
        """委托信息查询回调"""
        if self.checkDataError(data):
            return
        
        rawData = data['data']
        
        for d in rawData['orders']:
            self.localNo += 1
            localNo = str(self.localNo)
            orderId = str(d['order_id'])
            
            self.localNoDict[localNo] = orderId
            self.orderIdDict[orderId] = localNo
            
            if orderId not in self.orderDict:
                order = VtOrderData()
                order.gatewayName = self.gatewayName
                
                order.symbol = d['symbol']
                order.exchange = self.gatewayName
                order.vtSymbol = '.'.join([order.symbol, order.exchange])
    
                order.orderID = localNo
                order.vtOrderID = '.'.join([self.gatewayName, order.orderID])
                
                order.price = d['price']
                order.totalVolume = d['amount']
                order.direction, priceType = priceTypeMap[d['type']]
                date, order.orderTime = self.generateDateTime(d['create_date'])
                
                self.orderDict[orderId] = order
            else:
                order = self.orderDict[orderId]
                
            order.tradedVolume = d['deal_amount']
            order.status = statusMap[d['status']]            
            
            self.gateway.onOrder(copy(order))

    #----------------------------------------------------------------------
    def onSubSpotOrder(self, data):
        """交易数据"""
        rawData = data["data"]
        orderId = str(rawData['orderId'])  
        
        # 获取本地委托号
        if orderId in self.orderIdDict:
            localNo = self.orderIdDict[orderId]
        else:
            try:
                localNo = self.localNoQueue.get_nowait()
            except Empty:
                self.localNo += 1
                localNo = str(self.localNo)
        
        self.localNoDict[localNo] = orderId
        self.orderIdDict[orderId] = localNo        

        # 获取委托对象
        if orderId in self.orderDict:
            order = self.orderDict[orderId]
        else:
            order = VtOrderData()
            order.gatewayName = self.gatewayName
            order.symbol = rawData['symbol']
            order.exchange = self.gatewayName
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = localNo
            order.vtOrderID = '.'.join([self.gatewayName, localNo])
            order.direction, priceType = priceTypeMap[rawData['tradeType']]
            order.price = float(rawData['tradeUnitPrice'])
            order.totalVolume = float(rawData['tradeAmount'])
            date, order.orderTime = self.generateDateTime(rawData['createdDate'])
        
        lastTradedVolume = order.tradedVolume
        
        order.status = statusMap[rawData['status']]
        order.tradedVolume = float(rawData['completedTradeAmount'])
        self.gateway.onOrder(copy(order))
        
        # 成交信息
        if order.tradedVolume > lastTradedVolume:
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
    
            trade.symbol = order.symbol
            trade.exchange = order.exchange
            trade.vtSymbol = order.vtSymbol
            
            self.tradeID += 1
            trade.tradeID = str(self.tradeID)
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
            
            trade.orderID = order.orderID
            trade.vtOrderID = order.vtOrderID
            
            trade.direction = order.direction
            trade.price = float(rawData['averagePrice'])
            trade.volume = order.tradedVolume - lastTradedVolume
            
            trade.tradeTime = datetime.now().strftime('%H:%M:%S')
            self.gateway.onTrade(trade)
        
        # 撤单
        if localNo in self.cancelDict:
            req = self.cancelDict[localNo]
            self.spotCancel(req)
            del self.cancelDict[localNo]        

    #----------------------------------------------------------------------        
    def onSubSpotBalance(self, data):
        """"""
        rawData = data['data']
        free = rawData['info']['free']
        freezed = rawData['info']['freezed']
        
        for symbol in free.keys():
            pos = VtPositionData()
            pos.gatewayName = self.gatewayName
            pos.symbol = symbol
            pos.exchange = self.gatewayName
            pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
            pos.direction = DIRECTION_LONG
            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])
            pos.frozen = float(freezed[symbol])
            pos.position = pos.frozen + float(free[symbol])

            self.gateway.onPosition(pos)
    
    #----------------------------------------------------------------------
    def init(self, apiKey, secretKey, trace, symbols):
        """初始化接口"""
        self.symbols = symbols
        self.initCallback()
        self.connect(OKEX_SPOT_HOST, apiKey, secretKey, trace)
        self.writeLog(u'现货接口初始化成功')

    #----------------------------------------------------------------------
    def sendOrder(self, req):
        """发单"""
        if req.priceType == 0:
            req.priceType = PRICETYPE_LIMITPRICE
        else:
            req.priceType = PRICETYPE_MARKETPRICE

        type_ = priceTypeMapReverse[(req.direction, req.priceType)]
        result = self.spotOrder(req.symbol, type_, str(req.price), str(req.volume))
        # 若请求失败，则返回空字符串委托号
        if not result:
            return ''
        
        # 本地委托号加1，并将对应字符串保存到队列中，返回基于本地委托号的vtOrderID
        self.localNo += 2
        self.localNoQueue.put(str(self.localNo))
        vtOrderID = '.'.join([self.gatewayName, str(self.localNo)])
        # 缓存委托信息
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.symbol = req.symbol
        order.exchange = self.gatewayName
        order.contractType = None
        order.vtSymbol = req.vtSymbol
        order.orderID= str(self.localNo)
        order.vtOrderID = vtOrderID
        order.direction = req.direction
        order.offset = req.offset
        order.price = req.price
        order.totalVolume = req.volume
        
        self.localOrderDict[str(self.localNo)] = order
        
        # self.localNoDict[str(self.localNo)]
        return vtOrderID
    
    #----------------------------------------------------------------------
    def cancelOrder(self, req):
        """撤单"""
        localNo = req.orderID
        if localNo in self.localNoDict:
            orderID = self.localNoDict[localNo]
            self.spotCancelOrder(req.symbol, orderID)
        else:
            # 如果在系统委托号返回前客户就发送了撤单请求，则保存
            # 在cancelDict字典中，等待返回后执行撤单任务
            self.cancelDict[localNo] = req

    #----------------------------------------------------------------------
    def generateDateTime(self, s):
        """生成时间"""
        dt = datetime.fromtimestamp(float(s)/1e3)
        time = dt.strftime("%H:%M:%S.%f")
        date = dt.strftime("%Y%m%d")
        return date, time

    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速记录日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)

    #----------------------------------------------------------------------
    def checkDataError(self, data):
        """检查回报是否存在错误"""
        rawData = data['data']
        if 'error_code' not in rawData:
            return False
        else:
            error = VtErrorData()
            error.gatewayName = self.gatewayName
            error.errorID = rawData['error_code']
            error.errorMsg = u'请求失败，功能：%s' %data['channel']
            self.gateway.onError(error)
            return True

    #----------------------------------------------------------------------
    def subscribe(self, symbol):
        """订阅行情"""
        symbol = symbol
        
        self.subscribeSpotTicker(symbol)
        self.subscribeSpotDepth(symbol, 10)
        self.subscribeSpotDeals(symbol)
        self.subSpotOrder(symbol)
        self.subSpotBalance(symbol)

class FuturesApi(OkexFuturesApi):
    """OKEX的期货API实现"""
    def __init__(self, gateway):
        """Constructor"""
        super(FuturesApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称

        self.cbDict = {}
        self.tickDict = {}
        self.orderDict = {}
        self.posDict = {}
        self.channelSymbolMap = {}
        self.channelcontractTypeMap = {}
        
        self.localNo = 0                # 本地委托号
        self.localNoQueue = Queue()     # 未收到系统委托号的本地委托号队列
        self.localNoDict = {}           # key为本地委托号，value为系统委托号
        self.localOrderDict = {}        # key为本地委托号, value为委托对象
        self.orderIdDict = {}           # key为系统委托号，value为本地委托号
        self.cancelDict = {}            # key为本地委托号，value为撤单请求
        self.strategyDict = {}

        self.recordOrderId_BefVolume = {}       # 记录的之前处理的量

        self.cache_some_order = {}
        self.tradeID = 0
        self.symbolSizeDict = {}        # 保存合约代码和合约大小的印射关系
        self.contract_id ={}             # 用于持仓信息中, 对应rest查询的合约和ws查询的合约
    #----------------------------------------------------------------------
    def onMessage(self, data):
        """信息推送""" 
        channel = data.get('channel', '')
        if not channel:
            return

        if channel in self.cbDict:
            callback = self.cbDict[channel]
            callback(data)


    #----------------------------------------------------------------------
    def onError(self, data):
        """错误推送"""
        error = VtErrorData()
        error.gatewayName = self.gatewayName
        error.errorMsg = str(data)
        self.gateway.onError(error)
        
    #----------------------------------------------------------------------
    def onClose(self):
        """接口断开"""
        self.gateway.connected = False
        self.writeLog(u'期货服务器连接断开')
    
    #----------------------------------------------------------------------
    def onOpen(self):       
        """连接成功"""
        self.gateway.connected = True
        self.writeLog(u'期货服务器连接成功')
        
        self.login()
        
        # 推送合约数据
        for symbol in self.contracts:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName

            contract.symbol = symbol
            contract.exchange = self.gatewayName
            contract.contractType = symbol[4:]
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            contract.name = symbol
            contract.size = 0.00001
            contract.priceTick = 0.00001
            contract.productClass = PRODUCT_FUTURES
            self.gateway.onContract(contract)
    
    #----------------------------------------------------------------------
    def initCallback(self):
        """初始化回调函数"""
        for symbol in self.contracts:
            # channel和symbol映射
            contractType = symbol[4:]
            symbol = symbol[:3]
            self.channelSymbolMap["ok_sub_futureusd_%s_ticker_%s" %(symbol,contractType)] = symbol
            # self.channelSymbolMap["ok_sub_futureusd_%s_kline_this_week_week" %(symbol)] = symbol  ## WS并不会给历史K线，提供的是实时数据
            self.channelSymbolMap["ok_sub_futureusd_%s_depth_%s_10" %(symbol,contractType)] = symbol
            self.channelSymbolMap["ok_sub_futureusd_%s_trade_%s" %(symbol, contractType)] = symbol

            self.channelcontractTypeMap["ok_sub_futureusd_%s_ticker_%s" %(symbol,contractType)] = contractType
            self.channelcontractTypeMap["ok_sub_futureusd_%s_depth_%s_10" %(symbol,contractType)] = contractType
            self.channelcontractTypeMap["ok_sub_futureusd_%s_trade_%s" %(symbol, contractType)] = contractType

            # channel和callback映射
            self.cbDict["ok_sub_futureusd_%s_ticker_%s" % (symbol,contractType)] = self.onTicker
            self.cbDict["ok_sub_futureusd_%s_depth_%s_10" % (symbol,contractType)] = self.onDepth
            # self.cbDict["ok_sub_futureusd_%s_order" % symbol] = self.onSubFuturesOrder
            self.cbDict["ok_sub_futureusd_%s_trade_%s" %(symbol, contractType)] = self.onSubFuturesTrades
            
        self.cbDict["ok_sub_futureusd_userinfo"] = self.onSubFuturesBalance
        self.cbDict['ok_futureusd_userinfo'] = self.onFuturesUserInfo
        # self.cbDict['ok_futureusd_orderinfo'] = self.onFuturesOrderInfo
        self.cbDict['ok_futureusd_trade'] = self.onSubFuturesOrderError 
        self.cbDict['ok_sub_futureusd_trades'] = self.onFuturesOrderInfo
        # self.cbDict['ok_futureusd_order'] = self.onFuturesOrder
        # self.cbDict['ok_futureusd_cancel_order'] = self.onFuturesCancelOrder
        self.cbDict['ok_sub_futureusd_positions'] = self.onSubFuturesPosition
        # self.cbDict['ok_sub_futureusd_userinfo'] = self.subscribeFuturesUserInfo
        self.cbDict['login'] = self.onLogin
    
    #----------------------------------------------------------------------
    def onLogin(self, data):
        """"""
        # 查询持仓
        self.futuresUserInfo()
        # self.subscribeFuturesPositions()   # 没用，初始查询不给持仓信息

        # 订阅推送
        for symbol in self.contracts:
            contractType = symbol[4:]
            symbol = symbol[:3]
            self.subscribe(symbol,contractType)
            # self.rest_futures_position(symbol,contractType)  # 使用restful查询持仓信息

        self.writeLog(u'期货服务器登录成功')
    #----------------------------------------------------------------------
    def onTicker(self, data):
        """
        {'high': '724.306', 'limitLow': '693.093', 'vol': '852082', 'last': '714.333', 
        'low': '677.024', 'buy': '714.448', 'hold_amount': '599090', 'sell': '715.374', 
        'contractId': 201807060050052, 'unitAmount': '10', 'limitHigh': '735.946'}
        """
        channel = data['channel']
        # print('gw on tick',datetime.now(),data['data']['last'])
        symbol = self.channelSymbolMap[channel]
        contractType = self.channelcontractTypeMap[channel]
        symbol = symbol+'_'+contractType

        if symbol not in self.tickDict:

            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            tick.contractType = contractType
            tick.gatewayName = self.gatewayName
            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        d = data['data']
        tick.highPrice = float(d['high'])
        tick.lowPrice = float(d['low'])
        tick.lastPrice = float(d['last'])
        tick.volume = float(d['vol'].replace(',', ''))
        tick.volumeChange = 0
        tick.localTime = datetime.now()

        if tick.bidPrice1 and tick.lastVolume:
            newtick = copy(tick)
            self.gateway.onTick(newtick)
    #----------------------------------------------------------------------
    def onDepth(self, data):
        """
        {'binary': 0, 'channel': 'ok_sub_futureusd_btc_depth_this_week_10', 
        'data': {'asks': [[6785, 0, 0.0147, 264.3977, 17575], [6559.82, 30, 0.4573, 52.6851, 3442], [6534.79, 3, 0.0459, 29.6748, 1936], 
        [6532.37, 0, 0.0306, 27.2538, 1778], [6532.03, 2, 0.0306, 27.9454, 1823], [6523.49, 99, 1.5175, 17.2985, 1128], 
        [6523.15, 0, 1.5176, 16.1018, 1050], [6522.38, 0, 0.0306, 10.6901, 697], [6517.38, 80, 1.2274, 2.9305, 191]], 
        'bids': [[6512.65, 0, 1.2283, 1.2283, 80], [6509.74, 7, 0.1075, 8.7075, 567], [6507.45, 2, 0.0307, 14.8835, 969], 
        [6500.29, 0, 0.923, 33.9322, 2208], [6495.82, 0, 0.0307, 47.4715, 3088], [6494.98, 1, 0.0153, 45.4584, 2957], 
        [6494.74, 0, 0.0307, 47.5329, 3092],[6488.79, 30, 0.4623, 58.1995, 3784], [6481.17, 30, 0.4628, 64.3499, 4183], 
        [6468.13, 40, 0.6184, 110.2866, 7156], [6200, 71, 1.1451, 309.136, 19816], [6190, 99, 1.5993, 310.7353, 19915]], 
        'timestamp': 1530704626966}}
        """
        channel = data['channel']
        symbol = self.channelSymbolMap[channel]
        contractType = self.channelcontractTypeMap[channel]
        symbol = symbol+'_'+contractType

        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.contractType = contractType
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])

            tick.gatewayName = self.gatewayName

            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        d = data['data']
        tick.bidPrice1, tick.bidVolume1 = d['bids'][0][0],d['bids'][0][1]
        tick.bidPrice2, tick.bidVolume2 = d['bids'][1][0],d['bids'][1][1]
        tick.bidPrice3, tick.bidVolume3 = d['bids'][2][0],d['bids'][2][1]
        tick.bidPrice4, tick.bidVolume4 = d['bids'][3][0],d['bids'][3][1]
        tick.bidPrice5, tick.bidVolume5 = d['bids'][4][0],d['bids'][4][1]
        tick.bidPrice6, tick.bidVolume6 = d['bids'][5][0],d['bids'][5][1]
        tick.bidPrice7, tick.bidVolume7 = d['bids'][6][0],d['bids'][6][1]
        tick.bidPrice8, tick.bidVolume8 = d['bids'][7][0],d['bids'][7][1]
        tick.bidPrice9, tick.bidVolume9 = d['bids'][8][0],d['bids'][8][1]
        tick.bidPrice10, tick.bidVolume10 = d['bids'][9][0],d['bids'][9][1]
        tick.bidPrice1 = float(tick.bidPrice1)
        tick.bidPrice2 = float(tick.bidPrice2)
        tick.bidPrice3 = float(tick.bidPrice3)
        tick.bidPrice4 = float(tick.bidPrice4)
        tick.bidPrice5 = float(tick.bidPrice5)
        tick.bidPrice6 = float(tick.bidPrice6)
        tick.bidPrice7 = float(tick.bidPrice7)
        tick.bidPrice8 = float(tick.bidPrice8)
        tick.bidPrice9 = float(tick.bidPrice9)
        tick.bidPrice10 = float(tick.bidPrice10)
        tick.bidVolume1 = float(tick.bidVolume1)
        tick.bidVolume2 = float(tick.bidVolume2)
        tick.bidVolume3 = float(tick.bidVolume3)
        tick.bidVolume4 = float(tick.bidVolume4)
        tick.bidVolume5 = float(tick.bidVolume5)
        tick.bidVolume6 = float(tick.bidVolume6)
        tick.bidVolume7 = float(tick.bidVolume7)
        tick.bidVolume8 = float(tick.bidVolume8)
        tick.bidVolume9 = float(tick.bidVolume9)
        tick.bidVolume10 = float(tick.bidVolume10)

        tick.askPrice1, tick.askVolume1 = d['asks'][-1][0],d['asks'][-1][1]
        tick.askPrice2, tick.askVolume2 = d['asks'][-2][0],d['asks'][-2][1]
        tick.askPrice3, tick.askVolume3 = d['asks'][-3][0],d['asks'][-3][1]
        tick.askPrice4, tick.askVolume4 = d['asks'][-4][0],d['asks'][-4][1]
        tick.askPrice5, tick.askVolume5 = d['asks'][-5][0],d['asks'][-5][1]
        tick.askPrice6, tick.askVolume6 = d['asks'][-6][0],d['asks'][-6][1]
        tick.askPrice7, tick.askVolume7 = d['asks'][-7][0],d['asks'][-7][1]
        tick.askPrice8, tick.askVolume8 = d['asks'][-8][0],d['asks'][-8][1]
        tick.askPrice9, tick.askVolume9 = d['asks'][-9][0],d['asks'][-9][1]
        tick.askPrice10, tick.askVolume10 = d['asks'][-10][0],d['asks'][-10][1]
        tick.askPrice1 = float(tick.askPrice1)
        tick.askPrice2 = float(tick.askPrice2)
        tick.askPrice3 = float(tick.askPrice3)
        tick.askPrice4 = float(tick.askPrice4)
        tick.askPrice5 = float(tick.askPrice5)   
        tick.askPrice6 = float(tick.askPrice6)
        tick.askPrice7 = float(tick.askPrice7)
        tick.askPrice8 = float(tick.askPrice8)
        tick.askPrice9 = float(tick.askPrice9)
        tick.askPrice10 = float(tick.askPrice10)         
        tick.askVolume1 = float(tick.askVolume1)
        tick.askVolume2 = float(tick.askVolume2)
        tick.askVolume3 = float(tick.askVolume3)
        tick.askVolume4 = float(tick.askVolume4)
        tick.askVolume5 = float(tick.askVolume5)    
        tick.askVolume6 = float(tick.askVolume6)
        tick.askVolume7 = float(tick.askVolume7)
        tick.askVolume8 = float(tick.askVolume8)
        tick.askVolume9 = float(tick.askVolume9)
        tick.askVolume10 = float(tick.askVolume10)   

        tick.date, tick.time = self.generateDateTime(d['timestamp'])
        tick.volumeChange = 0
        tick.localTime = datetime.now()
        if tick.lastPrice and tick.lastVolume:
            newtick = copy(tick)
            self.gateway.onTick(newtick)
    #----------------------------------------------------------------------
    def onSubFuturesTrades(self,data):
        """接收最新成交量数据
        [交易序号, 价格, 成交量(张), 时间, 买卖类型，成交量(币-新增)]
        [
                "732916899",
                "999.49",
                "2.0",
                "15:25:04",
                "ask",
                "0.2001"
            ]
        """
        channel = data['channel']
        symbol = self.channelSymbolMap[channel]
        contractType = self.channelcontractTypeMap[channel]
        symbol = symbol+'_'+contractType

        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.exchange = self.gatewayName
            tick.contractType = contractType
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])

            tick.gatewayName = self.gatewayName

            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        for i in range(len(data['data'])):
            d = data['data'][i]
            tick.lastPrice = float(d[1])
            tick.lastVolume = float(d[2])
            tick.time = d[3]+".000000"
            tick.type = d[4]
            tick.volumeChange = 1
            tick.localTime = datetime.now()
            if tick.bidPrice1:
                newtick = copy(tick)
                self.gateway.onTick(newtick)

    def onFuturesUserInfo(self, data):
        """期货账户资金推送"""  
    #{'binary': 0, 'channel': 'ok_futureusd_userinfo', 'data': {'result': True, 

    # 'info': {'btc': {'balance': 0.00524741, 'rights': 0.00524741, 
    # 'contracts': [{'contract_type': 'this_week', 'freeze': 0, 'balance': 5.259e-05, 'contract_id':201807060000013, 
    # 'available': 0.00524741, 'profit': -5.259e-05, 'bond': 0, 'unprofit': 0}, 
    # {'contract_type': 'next_week', 'freeze': 0, 'balance': 0, 'contract_id': 201807130000034, 'available': 0.00524741, 
    # 'profit': 0, 'bond': 0, 'unprofit': 0}]}, 

    # 'eos': {'balance': 0, 'rights': 0, 'contracts': []}, 
    # 'ltc': {'balance': 0, 'rights': 0, 'contracts': []}}}}


    #    {'binary': 0, 'channel': 'ok_futureusd_userinfo', 'data': {'result': True, 
    #    'info': {'btc': {'risk_rate': 10000, 'account_rights': 0.00080068, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'btg': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'etc': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'bch': {'risk_rate': 10000, 'account_rights': 0.07406406, 'profit_unreal': 0, 'profit_real': 0.00017953, 'keep_deposit': 0}, 
    #    'xrp': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'eth': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'eos': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}, 
    #    'ltc': {'risk_rate': 10000, 'account_rights': 0, 'profit_unreal': 0, 'profit_real': 0, 'keep_deposit': 0}}}}

        if self.checkDataError(data):
            return
        print(data,"持仓的币种")
        contracts = data['data']['info']
        # 帐户信息
        for symbol in contracts.keys():
            fund = contracts[symbol]

            try:
                balance= float(fund['account_rights'])
                if balance:   ##过滤掉没有持仓的币种
                    account = VtAccountData()
                    account.coinSymbol = symbol
                    account.gatewayName = self.gatewayName
                    account.risk_rate = fund['risk_rate']
                    account.balance = balance
                    profit_real = fund['profit_real']
                    account.closeProfit = '%10.8f' % profit_real
                    profit_unreal = fund['profit_unreal']
                    account.positionProfit = '%10.8f' % profit_unreal
                    keep_deposit = fund['keep_deposit']
                    account.margin = '%10.9f' %keep_deposit
                    self.gateway.onAccount(account)    
                
            except:
                balance= float(fund['balance'])
                if balance:   ##过滤掉没有持仓的币种
                    account = VtAccountData()
                    account.coinSymbol = symbol
                    account.gatewayName = self.gatewayName
                    account.available = fund['rights']
                    account.balance = balance
                    # contract = fund['contracts']
                    # profit_real = fund['profit_real']
                    # account.closeProfit = '%10.8f' % profit_real
                    # profit_unreal = fund['profit_unreal']
                    # account.positionProfit = '%10.8f' % profit_unreal
                    # keep_deposit = fund['keep_deposit']
                    # account.margin = '%10.9f' %keep_deposit
                    self.gateway.onAccount(account)    
                self.writeLog(u'期货账户信息查询成功, 该账户是逐仓模式')
        self.writeLog(u'期货账户信息查询成功, 该账户是全仓模式')
        
        # 查询委托
        # for symbol in self.contracts:
        #     contractType = symbol[4:]
        #     symbol = symbol[:3]
        #     order_id = 1
        #     self.futuresOrderInfo(symbol,order_id, contractType,"2","1","1")        
            
    #----------------------------------------------------------------------
    def onFuturesOrderInfo(self, data):
        """委托信息查询回调
        {'lever_rate': 10.0, 'amount': 1.0, 'orderid': 1018500247351296, 'contract_id': 201807060050052, 
        'fee': 0.0, 'contract_name': 'BCH0706', 'unit_amount': 10.0, 'price_avg': 0.0, 'type': 1, 
        'deal_amount': 0.0, 'contract_type': 'this_week', 'user_id': ********, 'system_type': 0, 
        'price': 654.977, 'create_date_str': '2018-06-29 20:58:00', 'create_date': 1530277080437, 'status': 0}
        """
        if self.checkDataError(data):
            return
        rawData = data['data']
        orderId = str(rawData['orderid'])

        if orderId in self.orderIdDict:
            localNo = self.orderIdDict[orderId]
        else:
            try:
                localNo = self.localNoQueue.get_nowait()
            except Empty:
                self.localNo += 1
                localNo = str(self.localNo)

        self.localNoDict[localNo] = orderId
        self.orderIdDict[orderId] = localNo
        order = self.localOrderDict[localNo]
        # else:
        #     self.writeLog(u'非法订单')

        # if self.localOrderDict[localNo]:
        #     order = self.localOrderDict[localNo]

        order.price = rawData['price']
        order.price_avg = rawData['price_avg']
        order.direction, order.offset = futurepriceTypeMap[str(rawData['type'])]

        order.exchangeOrderID = orderId        
        order.user_id = rawData['user_id']
        order.gatewayName = self.gatewayName
        order.orderTime = rawData['create_date_str']
        order.deliverTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order.status = statusMap[rawData['status']] 
        
        self.orderDict[orderId] = order   #更新order信息
        lastTradedVolume = order.tradedVolume
        order.tradedVolume = float(rawData['deal_amount'])
        self.gateway.onOrder(copy(order))
        
        # 成交信息
        if order.tradedVolume > lastTradedVolume:
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
            trade.symbol = order.symbol
            trade.exchange = order.exchange
            trade.vtSymbol = order.vtSymbol
            
            self.tradeID += 1
            trade.tradeID = str(self.tradeID)
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
            
            trade.orderID = order.orderID
            trade.vtOrderID = order.vtOrderID
            trade.exchangeOrderID = order.exchangeOrderID
            trade.direction = order.direction
            trade.offset = order.offset
            trade.price = float(rawData['price_avg'])
            trade.volume = order.tradedVolume - lastTradedVolume
            trade.tradeTime = order.deliverTime
            self.gateway.onTrade(trade)
        
        # 撤单
        if localNo in self.cancelDict:
            req = self.cancelDict[localNo]
            self.cancelOrder(req)
            del self.cancelDict[localNo]  
        
    #----------------------------------------------------------------------
      
    def onFuturesRejectedOrder(self, data):
        """"""
        # 如果委托失败，则通知委托被拒单的信息
        if self.checkDataError(data):
            try:
                localNo = self.localNoQueue.get_nowait()
            except Empty:
                return
            
        order = self.localOrderDict[localNo]
        order.status = STATUS_REJECTED
        self.gateway.onOrder(order)
    
    #----------------------------------------------------------------------  
    def onSubFuturesOrderError(self, data):
        """ 下单报错信息"""
        if self.checkDataError(data):
            return
        rawData = data["data"]
        if rawData['result']:
            orderId = str(rawData['order_id'])  
        else:
            print("下单报错信息",rawData['error_code'])
    #----------------------------------------------------------------------
        
    def onSubFuturesBalance(self, data):
        """
        {'binary': 0, 'channel': 'ok_sub_futureusd_userinfo', 
        'data': {'symbol': 'eth_usd', 'balance': 0.03080528, 'unit_amount': 10.0, 
        'profit_real': 0.00077335, 'keep_deposit': 0.002298829}}
        """
        if self.checkDataError(data):
            return
        rawData = data['data']

        # 帐户信息更新

        account = VtAccountData()
        account.coinSymbol = rawData['symbol'][:3]
        account.gatewayName = self.gatewayName
        account.balance = rawData['balance']
        profit_real = rawData['profit_real']
        account.closeProfit = '%10.8f' % profit_real
        keep_deposit = rawData['keep_deposit']
        account.margin = '%10.9f' %keep_deposit
        self.gateway.onAccount(account)  
        
        self.writeLog(u'期货账户信息更新成功')

    #--------------------------------------------------------------------
    def onSubFuturesPosition(self,data):
        """
        {'binary': 0, 'channel': 'ok_sub_futureusd_positions', 
        'data': {'symbol': 'bch_usd', 'user_id': ***********, 
        'positions': [{'bondfreez': 0.0, 'margin': 0.0, 'avgprice': 660.97060244,'eveningup': 0.0, 
        'contract_id': 201807130050065, 'hold_amount': 0.0, 'contract_name': 'BCH0713','realized': -0.00316062, 
        'position': 1, 'costprice': 660.97060244, 'position_id': 1017505776168960}
        , {'bondfreez': 0.0, 'margin': 0.0, 'avgprice': 659.89775978, 'eveningup': 2.0, 'contract_id': 2018
        07130050065, 'hold_amount': 2.0, 'contract_name': 'BCH0713', 'realized': -0.00316062, 'position': 2
        , 'costprice': 659.89775978, 'position_id': 1017505776168960}]}}        
        """
        if self.checkDataError(data):
            return
        # if not self.contract_id:   #判断REST的持仓信息是否已经推送
        #     return
            
        symbol = data['data']['symbol']
        position = data['data']['positions']
        contract_id_ = position[0]['contract_id']

        date_one = datetime(int(contract_id_/100000000000), int(contract_id_/1000000000)%100, int(contract_id_/10000000)%100)
        date_temp = datetime.now()
        date_two = datetime(date_temp.year,date_temp.month,date_temp.day)
        delta_datetime=(date_one - date_two).days

        if delta_datetime<7:
            vtSymbol = symbol[:3] + '_this_week'
        elif delta_datetime>14:
            vtSymbol = symbol[:3] + '_quarter'
        else:
            vtSymbol = symbol[:3] + '_next_week'
            
        self.contract_id[str(contract_id_)] = vtSymbol
        pos = VtPositionData()
        pos.gatewayName = self.gatewayName
        pos.symbol = vtSymbol
        pos.exchange = self.gatewayName
        pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])

        longPos = copy(pos)
        longPos.direction = DIRECTION_LONG
        # 多头仓位
        longPosName = '.'.join([pos.vtSymbol, DIRECTION_LONG])
        try:
            longPos = self.posDict[longPosName]
        except KeyError:
            longPos = copy(pos)
            longPos.direction = DIRECTION_LONG
            longPos.vtPositionName = longPosName
            self.posDict[longPosName] = longPos
        longPos.position = position[0]['hold_amount']
        longPos.price = position[0]['avgprice']
        longPos.frozen = longPos.position - position[0]['eveningup']
        profit = position[0]['realized']
        longPos.positionProfit = '%10.8f' % profit
        longPos.vtPositionName = '.'.join([pos.vtSymbol, longPos.direction])


        shortPos = copy(pos)
        shortPos.direction = DIRECTION_SHORT
        # 空头仓位    
        shortPosName = '.'.join([pos.vtSymbol, DIRECTION_SHORT])
        try:
            shortPos = self.posDict[shortPosName]
        except KeyError:
            shortPos = copy(pos)
            shortPos.direction = DIRECTION_SHORT
            shortPos.vtPositionName = shortPosName 
            self.posDict[shortPosName] = shortPos
        shortPos.position = position[1]['hold_amount']
        shortPos.price = position[1]['avgprice']
        shortPos.frozen = shortPos.position - position[1]['eveningup']
        profit = position[1]['realized']
        shortPos.positionProfit = '%10.8f' % profit
        shortPos.vtPositionName = '.'.join([pos.vtSymbol, shortPos.direction])            
            
        self.gateway.onPosition(longPos)
        self.gateway.onPosition(shortPos)
        
    #----------------------------------------------------------------------
    def init(self, apiKey, secretKey, trace, contracts):
        """初始化接口"""

        self.contracts = contracts
        self.initCallback()
        self.connect(OKEX_FUTURES_HOST, apiKey, secretKey, trace)
        self.writeLog(u'期货接口初始化成功')

    #----------------------------------------------------------------------
    def sendOrder(self, req):
        """发单"""
        type_ = futurepriceTypeMapReverse[(req.direction, req.offset)]

        if req.priceType == PRICETYPE_LIMITPRICE:
            req.priceType = 0
        elif req.priceType == PRICETYPE_MARKETPRICE:
            req.priceType = 1

        result = self.futuresTrade(req.symbol, req.contractType ,type_, req.price, req.volume, req.priceType ,"10")
        # 若请求失败，则返回空字符串委托号
        if not result:
            return ''
        
        # 本地委托号加1，并将对应字符串保存到队列中，返回基于本地委托号的vtOrderID
        self.localNo += 1
        self.localNoQueue.put(str(self.localNo))
        vtOrderID = '.'.join([self.gatewayName, str(self.localNo)])
        # 缓存委托信息
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.symbol = req.symbol
        order.exchange = self.gatewayName
        order.vtSymbol = '.'.join([order.symbol, order.exchange])
        order.contractType = req.contractType
        order.orderID= str(self.localNo)
        order.vtOrderID = vtOrderID
        order.direction = req.direction
        order.price = req.price
        order.totalVolume = req.volume
        order.bystrategy = req.bystrategy
        
        self.localOrderDict[str(self.localNo)] = order
        self.localNoDict[str(self.localNo)] = vtOrderID
        return vtOrderID
    

    #---------------------------------------------------------------------------
    def cancelOrder(self, req):
        """撤单"""
        localNo = req.orderID
        if localNo in self.localNoDict:
            orderID = self.localNoDict[localNo]

            self.futuresCancelOrder(req.symbol, orderID, req.contractType)
        else:
            # 如果在系统委托号返回前客户就发送了撤单请求，则保存
            # 在cancelDict字典中，等待返回后执行撤单任务
            self.cancelDict[localNo] = req

    #----------------------------------------------------------------------
    def generateDateTime(self, s):
        """生成时间"""
        dt = datetime.fromtimestamp(float(s)/1e3)
        time = dt.strftime("%H:%M:%S.%f")
        date = dt.strftime("%Y%m%d")
        return date, time

    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速记录日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)

    #----------------------------------------------------------------------
    def checkDataError(self, data):
        """检查回报是否存在错误"""
        rawData = data['data']
        if 'error_code' not in rawData:
            return False
        else:
            error = VtErrorData()
            error.gatewayName = self.gatewayName
            error.errorID = rawData['error_code']
            error.errorMsg = u'请求失败，功能：%s' %data['channel']
            self.gateway.onError(error)
            return True

    #----------------------------------------------------------------------
    def subscribe(self, symbol,contractType):
        """订阅行情"""
        self.subsribeFuturesTicker(symbol,contractType)
        # self.subscribeFuturesKline(symbol,"this_week","30min")
        self.subscribeFuturesDepth(symbol,contractType)
        self.subscribeFuturesTrades(symbol,contractType)
        # self.subscribeFuturesUserInfo()
    #------------------------------------------------------
    #Restful 配置

    def rest_futures_position(self, symbol,contractType):
        data = self.future_position(symbol,contractType)
        """
        {'result': True, 
        'holding': [
            {'buy_price_avg': 653.83300536, 'symbol': 'bch_usd', 'lever_rate': 10, 'buy_available': 0, 
            'contract_id': 201807060050052, 'buy_amount': 0, 'buy_profit_real': -0.0011777, 
            'contract_type': 'this_week', 'sell_amount': 0, 'sell_price_cost': 655.176, 
            'buy_price_cost': 653.83300536, 'create_date': 1529979371000,'sell_price_avg': 655.176, 
            'sell_profit_real': -0.0011777, 'sell_available': 0}], 'force_liqu_price': '0.000'}
        """
        # print("restonFuturesPosition",data)
        if data['result']:
            if not data['holding']:
                return
            position = data['holding'][0]
            symbol = position['symbol'][:3]
            contract_type = position['contract_type']
            gateway = self.gatewayName
            vtSymbol = symbol + '_'+contract_type +'.'+ gateway
            self.contract_id[str(position['contract_id'])] =vtSymbol

            pos1 = VtPositionData()
            pos1.gatewayName = gateway
            pos1.symbol = vtSymbol
            pos1.vtSymbol = pos1.symbol
            pos1.exchange = self.gatewayName
            pos1.direction = DIRECTION_LONG
            pos1.vtPositionName = '.'.join([pos1.vtSymbol, pos1.direction])
            
            # 汇总总仓
            pos1.position = position['buy_amount']
            pos1.positionProfit = position['buy_profit_real']
            pos1.price =  position['buy_price_avg']
            pos1.frozen = pos1.position - position['buy_available']
            print(pos1.vtPositionName,pos1.position)
            self.gateway.onPosition(pos1)

            
            pos2 = VtPositionData()
            pos2.gatewayName = gateway
            pos2.symbol = vtSymbol
            pos2.vtSymbol = pos2.symbol
            pos2.exchange = self.gatewayName
            pos2.direction = DIRECTION_SHORT
            pos2.vtPositionName = '.'.join([pos2.vtSymbol, pos2.direction])

            # 汇总总仓
            pos2.position = position['sell_amount']
            pos2.positionProfit = position['sell_profit_real']
            pos2.price =  position['sell_price_avg']
            pos2.frozen = pos2.position - position['sell_available']
            print(pos2.vtPositionName,pos2.position)
            self.gateway.onPosition(pos2)
            # # 遍历推送
            # for pos in list(self.posDict.values()):
            #     self.gateway.onPosition(pos)
            # # 清空缓存
            # self.posDict.clear()
        else:
            # {'result': False, 'error_code': 20022, 'interface': '/api/v1/future_position_4fix'}
            return data['error_code']


