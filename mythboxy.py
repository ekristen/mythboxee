import mc

def CreateConnection():
	try:
		pin = mc.GetApp().GetLocalConfig().GetValue("pin")
		if not pin:
			pin = 0000
		db = mythtv.MythDB(SecurityPin=pin)
	except Exception, e:
		if e.ename == 'DB_CREDENTIALS':
			mc.ShowDialogNotification("Unable to connect, try to manually set the security pin.")
			mc.ActivateWindow(14006)
			mc.GetWindow(14006).GetControl(6010).SetVisible(True)
			mc.GetWindow(14006).GetControl(6020).SetVisible(False)
			mc.GetWindow(14006).GetControl(6011).SetFocus()
		elif e.ename == 'DB_CONNECTION':
			mc.ActivateWindow(14006)
			mc.GetWindow(14006).GetControl(6010).SetVisible(False)
			mc.GetWindow(14006).GetControl(6020).SetVisible(True)
			mc.GetWindow(14006).GetControl(6021).SetFocus()

