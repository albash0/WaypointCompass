"""Electrical and placement source for the compact compass, rev C1 prototype."""
import json
from pathlib import Path
from sexpr import symbol,pins,children
ROOT=Path(__file__).resolve().parent
PARTS=[]
def add(ref,value,libsym,footprint,nets,at,angle=0,side='back',mpn='',note='',custom=None):
    lib,name=libsym.split(':') if libsym else ('','')
    pp=pins(symbol(lib,name)) if libsym else custom
    PARTS.append(dict(ref=ref,value=value,libsym=libsym,footprint=footprint,nets={str(k):v for k,v in nets.items()},at=at,angle=angle,side=side,mpn=mpn or value,note=note,pins=pp))
def custompins(items):return [{'number':str(i),'name':n,'type':t} for i,n,t in items]
def r(ref,v,n1,n2,at,angle=0,note=''):
    add(ref,v,'Device:R','Resistor_SMD:R_0603_1608Metric',{1:n1,2:n2},at,angle,note=note)
def c(ref,v,n1,n2,at,angle=0,large=False):
    add(ref,v,'Device:C','Capacitor_SMD:C_0805_2012Metric' if large else 'Capacitor_SMD:C_0603_1608Metric',{1:n1,2:n2},at,angle,note='X7R; 10 V minimum; account for DC bias')
# S3 MINI-1U avoids placing a PCB RF antenna immediately behind the metal LCD.
mcu={1:'GND',2:'GND',3:'3V3',4:'BOOT',5:'BAT_ADC',6:'BUTTON_2',10:'TFT_RST',12:'I2C_SDA',13:'I2C_SCL',14:'TFT_SCK',15:'TFT_MOSI',16:'TFT_CS',17:'TFT_DC',23:'USB_M_MCU',24:'USB_P_MCU',39:'GPS_RX',40:'GPS_TX',45:'MCU_EN'}
mcu.update({i:'GND' for i in [42,43]+list(range(46,66))})
add('U1','ESP32-S3-MINI-1U-N4R2','RF_Module:ESP32-S3-MINI-1U','RF_Module:ESP32-S2-MINI-1U',mcu,[24,20],mpn='ESP32-S3-MINI-1U-N4R2',note='Optional external 2.4 GHz antenna; no RF used by compass firmware')
accel=custompins([(1,'SCL','input'),(2,'CS','input'),(3,'SA0','input'),(4,'SDA','bidirectional'),(5,'RES_GND','passive'),(6,'GND','power_in'),(7,'GND','passive'),(8,'GND','passive'),(9,'VDD','power_in'),(10,'VDD_IO','power_in'),(11,'INT2','output'),(12,'INT1','output')])
add('U2','LIS2DH12TR',None,'Package_LGA:LGA-12_2x2mm_P0.5mm',{1:'I2C_SCL',2:'3V3',3:'GND',4:'I2C_SDA',5:'GND',6:'GND',7:'GND',8:'GND',9:'3V3',10:'3V3'},[11,23],custom=accel,note='I2C 0x18; +X must be mapped to device front')
add('U3','LIS2MDLTR','Sensor_Magnetic:LIS2MDL','Package_LGA:LGA-12_2x2mm_P0.5mm',{1:'I2C_SCL',3:'3V3',4:'I2C_SDA',5:'MAG_C1',6:'GND',8:'GND',9:'3V3',10:'3V3'},[11,17],note='I2C 0x1E; NC pins 2/11/12 left open')
# Power path: VBUS -> charger -> SYS -> 3.3 V buck-boost / 5 V GPS boost.
add('U4','BQ24074RGTR','Battery_Management:BQ24074RGT','Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm',{1:'BAT_TS',2:'VBAT',3:'VBAT',4:'GND',5:'GND',6:'VBUS',7:'PGOOD_N',8:'GND',9:'CHG_N',10:'SYS',11:'SYS',12:'CHG_ILIM',13:'VBUS',14:'CHG_TMR',16:'CHG_ISET',17:'GND'},[40,9],note='4.2 V single-cell; fixed 500 mA USB input mode; 100 mA default charge')
add('U5','TPS63060DSCR','Regulator_Switching:TPS63060','Package_SON:Texas_S-PWSON-N10',{1:'BB_L1',2:'SYS',3:'POWER_EN',4:'SYS',6:'BB_AUX',7:'GND',8:'BB_FB',9:'3V3',10:'BB_L2',11:'GND'},[41,20],note='3.3 V buck-boost; forced PWM for predictable sensor noise')
boost=custompins([(1,'FB','input'),(2,'EN','input'),(3,'VIN','power_in'),(4,'GND','power_in'),(5,'SW','passive'),(6,'VOUT','power_out')])
add('U6','TPS61023DRLR',None,'Package_TO_SOT_SMD:SOT-563',{1:'GPS_FB',2:'POWER_EN',3:'SYS',4:'GND',5:'GPS_SW',6:'GPS_5V'},[45,29],custom=boost,note='5 V GPS breakout supply while running from battery')
add('U7','BQ29700DSET','Battery_Management:BQ297xy','Package_SON:WSON-6_1.5x1.5mm_P0.5mm',{2:'PROT_COUT',3:'PROT_DOUT',4:'CELL_NEG',5:'PROT_BAT',6:'PROT_VM'},[33,33],note='4.275 V / 2.8 V cell protection; cell negative isolated from system GND')
add('Q1','AO3400A','Transistor_FET:AO3400A','Package_TO_SOT_SMD:SOT-23',{1:'PROT_DOUT',2:'CELL_NEG',3:'FET_MID'},[33,36],180,note='Discharge FET; common drain with Q2')
add('Q2','AO3400A','Transistor_FET:AO3400A','Package_TO_SOT_SMD:SOT-23',{1:'PROT_COUT',2:'GND',3:'FET_MID'},[29,36],note='Charge FET; common drain with Q1')
add('U8','USBLC6-2SC6','Power_Protection:USBLC6-2SC6','Package_TO_SOT_SMD:SOT-23-6',{1:'USB_M',2:'GND',3:'USB_P',4:'USB_P',5:'VBUS',6:'USB_M'},[20,31],note='USB ESD diode array placed near connector')
usb={p['number']:('GND' if p['name'] in ('GND','SHIELD') else 'VBUS' if p['name']=='VBUS' else 'USB_P' if p['name']=='D+' else 'USB_M' if p['name']=='D-' else p['name'] if p['name'] in ('CC1','CC2') else None) for p in pins(symbol('Connector','USB_C_Receptacle_USB2.0_16P'))}
add('J1','USB-C USB2','Connector:USB_C_Receptacle_USB2.0_16P','Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',usb,[20,38],note='USB device; use a 5 V USB source capable of 500 mA')
# Front TFT landing reused; keep the cheap existing display module.
tftp=custompins([(1,'VCC','power_in'),(2,'GND','power_in'),(3,'SCL','input'),(4,'SDA','input'),(5,'DC','input'),(6,'CS','input'),(7,'RST','input')])
add('J2','GC9A01 TFT',None,'CompassCarrier:GC9A01_TFT_Socket',{1:'GPS_5V',2:'GND',3:'TFT_SCK',4:'TFT_MOSI',5:'TFT_DC',6:'TFT_CS',7:'TFT_RST'},[51.74,20],90,'front',custom=tftp,note='Screen centered (27,20); 2.54 mm straight-header spacer; 5 V supply as on working prototype')
add('J3','BATTERY JST-PH2','Connector_Generic:Conn_01x02','Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal',{1:'VBAT',2:'CELL_NEG'},[39,37],note='Pin 1 positive; 300-1000 mAh 1S 4.2 V-charge Li-ion/LiPo; verify plug polarity')
add('J4','GPS JST-SH4','Connector_Generic:Conn_01x04','Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',{1:'GPS_VCC',2:'GPS_RX',3:'GPS_TX',4:'GND'},[50,20],90,note='New SH cable: VCC,RX,TX,GND; UART is 3.3 V')
add('J5','BATTERY NTC','Connector_Generic:Conn_01x02','Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal',{1:'BAT_TS',2:'GND'},[49,35],note='External 10k 103AT-2 thermistor attached to cell; no NTC = charge inhibited')
add('JP1','GPS 3V3/5V','Jumper:Jumper_3_Open','Jumper:SolderJumper-3_P1.3mm_Open_Pad1.0x1.5mm',{1:'3V3',2:'GPS_VCC',3:'GPS_5V'},[48,24],90,note='Bridge 2-3 by default for 5 V breakout; never bridge both sides')
add('JP2','FAST 250mA','Jumper:Jumper_2_Open','Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm',{1:'CHG_ISET',2:'FAST_R'},[40,3],note='Open=100 mA for 300-500 mAh; bridge=250 mA for 500-1000 mAh cells rated for it')
add('SW1','CAL/BOOT','Switch:SW_Push','Button_Switch_THT:SW_PUSH_6mm',{1:'BOOT',2:'GND'},[1.75,4.75],side='front',note='Body center (5,7); GPIO0 held on reset enters ROM bootloader')
add('SW2','ACTION','Switch:SW_Push','Button_Switch_THT:SW_PUSH_6mm',{1:'BUTTON_2',2:'GND'},[1.75,30.75],side='front',note='Body center (5,33); GPIO2')
add('SW3','RESET','Switch:SW_Push','Button_Switch_SMD:SW_SPST_TL3342',{1:'MCU_EN',2:'GND'},[10,29],note='Rear reset button')
add('SW4','POWER','Switch:SW_SPDT','Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN',{1:'GND',2:'POWER_EN',3:'SYS'},[49,8],90,note='Off grounds regulator enable; charger stays active')
# Sensor and MCU support.
r('R1','4.7k','3V3','I2C_SDA',[12,26]);r('R2','4.7k','3V3','I2C_SCL',[9,26])
c('C1','100n','3V3','GND',[8,23],90);c('C2','1u','3V3','GND',[14,23],90)
c('C3','100n','3V3','GND',[8,17],90);c('C4','1u','3V3','GND',[14,17],90);c('C5','220n','MAG_C1','GND',[11,20])
r('R3','10k','3V3','MCU_EN',[14,10]);c('C6','1u','MCU_EN','GND',[17,10])
r('R4','10k','3V3','BOOT',[11,10]);r('R5','10k','3V3','BUTTON_2',[8,10])
c('C7','10u','3V3','GND',[14,12],large=True);c('C8','100n','3V3','GND',[11,12])
r('R6','22','USB_M','USB_M_MCU',[23,30],90);r('R7','22','USB_P','USB_P_MCU',[25,30],90)
r('R8','5.1k','CC1','GND',[14,33],90);r('R9','5.1k','CC2','GND',[27,33],90)
c('C9','100n','VBUS','GND',[23,33])
r('R10','330k','VBAT','BAT_ADC',[31,11]);r('R11','100k','BAT_ADC','GND',[31,8]);c('C10','100n','BAT_ADC','GND',[31,5])
# Charger: 890/8870 = 100.3 mA nominal. Parallel 5.90k selects 251 mA.
r('R12','8.87k','CHG_ISET','GND',[37,5]);r('R13','5.90k','FAST_R','GND',[43,3])
r('R14','3.16k','CHG_ILIM','GND',[36,11],90,note='ILIM unused in fixed USB500 mode; populated for defined pin bias')
r('R15','71.5k','CHG_TMR','GND',[37,8],90,note='9.53 h typical timer; 7.15-11.92 h factor limits; 1000 mAh use 250 mA mode')
c('C11','1u','VBUS','GND',[43,6],90);c('C12','4.7u','VBAT','GND',[44,10],90);c('C13','4.7u','SYS','GND',[40,13])
r('R16','2.2k','VBUS','LED_CHG_A',[47,12]);add('D1','CHARGE amber','Device:LED','LED_SMD:LED_0603_1608Metric',{1:'CHG_N',2:'LED_CHG_A'},[50,12],note='Charge active / fault indicator')
r('R17','10k','3V3','PGOOD_N',[34,14]);r('R18','100k','POWER_EN','GND',[46,5])
# TPS63060 power loop: 1.5 uH / 44uF; FB = 0.5 * (1+560k/100k) = 3.3 V.
add('L1','1.5uH >=3A','Device:L','Inductor_SMD:L_Vishay_IFSC-1515AH_4x4x1.8mm',{1:'BB_L1',2:'BB_L2'},[41,16],note='Use shielded 1.5 uH; Isat >=3 A; verify land pattern for actual BOM part')
c('C14','10u','SYS','GND',[37,18],90,True);c('C15','100n','SYS','GND',[37,20],90)
c('C16','22u','3V3','GND',[45,18],90,True);c('C17','22u','3V3','GND',[45,21],90,True)
c('C18','100n','BB_AUX','GND',[43,23]);r('R19','560k','3V3','BB_FB',[40,24]);r('R20','100k','BB_FB','GND',[37,24])
# GPS boost: 0.6 * (1+732k/100k) = 4.992 V.
add('L2','1uH >=2A','Device:L','Inductor_SMD:L_0805_2012Metric',{1:'SYS',2:'GPS_SW'},[45,26],note='Shielded power inductor; >=2 A Isat; select exact part before production')
c('C19','10u','SYS','GND',[42,27],90,True);c('C20','22u','GPS_5V','GND',[49,29],90,True);c('C21','22u','GPS_5V','GND',[49,32],90,True)
r('R21','732k','GPS_5V','GPS_FB',[45,32]);r('R22','100k','GPS_FB','GND',[42,32])
# Cell protection: Q1/Q2 common drain, sources cell negative and pack negative.
r('R23','330','VBAT','PROT_BAT',[33,30]);r('R24','2.2k','GND','PROT_VM',[36,33],90)
c('C22','100n','PROT_BAT','CELL_NEG',[30,32],90)
# Test pads, without tall debug headers.
for i,(name,xy) in enumerate([('GND',[5,20]),('3V3',[5,23]),('VBAT',[5,17]),('SYS',[5,26]),('GPS_RX',[26,9]),('GPS_TX',[23,9]),('MCU_EN',[20,9]),('BOOT',[20,6])],1):
 add('TP'+str(i),name,'Connector:TestPoint','TestPoint:TestPoint_Pad_D1.0mm',{1:name},xy)
# Final compact placement, millimeters from the upper-left board corner.
placement = {
 'J1':([22,36.2],180), 'J3':([42,33],180), 'J4':([37,3.4],0), 'J5':([3.4,21],90),
 'SW3':([12.5,31],0), 'SW4':([23,4],0), 'JP1':([48,33],90), 'JP2':([45.5,3],0),
 'U4':([40,10],0), 'U5':([39.5,22.5],0), 'L1':([39.5,27.2],0),
 'U6':([48.5,21.5],0), 'L2':([48.5,18.5],0), 'U8':([22,29.6],0),
 'Q1':([34,37.5],180), 'Q2':([30,37.5],0),
 'R3':([14,9.5],0), 'C6':([17,9.5],0), 'R5':([8,13],0), 'C8':([11,13.5],0),
 'R6':([21,10],90), 'R7':([23,10],90), 'R8':([14,36.5],90), 'R9':([28,29.5],90), 'C9':([28,32.5],90),
 'R12':([36,11],0), 'R13':([46,5.5],0), 'R14':([37,13.5],90), 'R15':([37,8.5],90),
 'R16':([48,5],90), 'D1':([49,7.5],0), 'R17':([34,12],0), 'R18':([34,15],0),
 'C13':([40,14],0), 'C14':([35.5,21],90), 'C15':([35.5,24],90),
 'C16':([44,21],90), 'C17':([44,24.6],90), 'C18':([44,15],0),
 'R19':([40,17],0), 'R20':([37,17],0), 'C19':([44.5,18],90),
 'C20':([48,24],0), 'C21':([48,26],0), 'R21':([45.2,28],0), 'R22':([44.7,30],0),
 'TP1':([6,12],0), 'TP2':([6,15],0), 'TP3':([11,3],0), 'TP4':([34,18],0),
 'TP5':([34,21],0), 'TP6':([34,27],0), 'TP7':([34,24],0), 'TP8':([14,28],0),
}
placement.update({'SW3':([13.5,4.5],0), 'U8':([14.2,31.5],0), 'TP3':([5,26],0),
 'C8':([12,14],0), 'R17':([34,12.5],0), 'C19':([44.5,17.4],90),
 'C15':([35.5,24.5],90), 'TP5':([33,21],0), 'TP7':([33,24],0),
 'R13':([45.5,4.8],0), 'R16':([46.5,7.7],90), 'R9':([29,29.5],90), 'C9':([28.5,33],90)})
placement.update({'R9':([29.9,29],0), 'C19':([44.5,17.55],90), 'C16':([44,21.1],90), 'C17':([44,24.7],90), 'R13':([45.5,5.1],0), 'TP1':([4.5,12],0)})
placement.update({'J1':([21.5,36.2],180), 'U8':([29.3,32.5],90), 'C22':([35.5,29.5],90), 'C9':([15,28.5],90), 'TP8':([6,28.5],0)})
placement.update({'C19':([46,13.5],90), 'C18':([42.8,19.5],90), 'C16':([45.3,21.5],90), 'C17':([45.3,25.1],90), 'C20':([48.2,24],0), 'C21':([48.2,26],0), 'R19':([43.2,22.7],90), 'R20':([43.2,24.8],90)})
placement.update({'R6':([23,10],90), 'R7':([21,10],90)})
for p in PARTS:
 if p['ref'] in placement: p['at'],p['angle']=placement[p['ref']]
 if p['ref'] in ('R19','R20'): p['footprint']='Resistor_SMD:R_0402_1005Metric'
 if p['ref']=='L1':
  p.update(mpn='IFSC1515AHER1R5M01',note='Vishay shielded 1.5 uH; 3.60 A nominal saturation current; 4 x 4 mm')
 if p['ref']=='L2':
  p.update(footprint='Inductor_SMD:L_Vishay_IHLP-1212',mpn='IHLP1212BZEV1R0M01',note='Vishay shielded 1 uH IHLP-1212BZ-01; 6.92 A typical saturation; 4.99 A typical thermal rating')
# Group into schematic blocks using label-connected pins; functional placement is independent of PCB position.
blocks={'U1':'mcu','U2':'sensors','U3':'sensors','U4':'charger','U5':'3v3','U6':'gpspower','U7':'protection','Q1':'protection','Q2':'protection','U8':'usb','J1':'usb','J2':'display','J3':'protection','J4':'display','J5':'charger','JP1':'display','JP2':'charger','SW1':'mcu','SW2':'mcu','SW3':'mcu','SW4':'3v3'}
for p in PARTS:
 ref=p['ref'];p['block']=blocks.get(ref,'sensors' if ref in ['R1','R2','C1','C2','C3','C4','C5'] else 'mcu' if ref in ['R3','R4','R5','C6','C7','C8','R10','R11','C10'] else 'usb' if ref in ['R6','R7','R8','R9','C9'] else 'charger' if ref in ['R12','R13','R14','R15','R16','R17','R18','C11','C12','C13','D1'] else '3v3' if ref in ['L1','C14','C15','C16','C17','C18','R19','R20'] else 'gpspower' if ref in ['L2','C19','C20','C21','R21','R22'] else 'protection' if ref in ['R23','R24','C22'] else 'test')
 # Missing nets mean physically unconnected pins, never silently grounded.
 for pin in p['pins']:p['nets'].setdefault(pin['number'],None)
config={'name':'WaypointCompassCompact','revision':'C1','size_mm':[54,40],'display_center_mm':[27,20],'layers':4,'parts':PARTS,'battery':{'chemistry':'1S Li-ion/LiPo, 4.2 V charge','capacity_mAh':[300,1000],'connector':'JST-PH 2.00 mm, pin1 positive','charge_mA_default':100,'charge_mA_fast':251,'external_ntc':'10k 103AT-2 attached to cell, J5'},'status':'Prototype design; bench validation required'}
(ROOT/'design.json').write_text(json.dumps(config,indent=2)+'\n')
print(len(PARTS),'physical components')
