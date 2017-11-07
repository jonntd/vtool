from vtool import util_file
from vtool import util



sg = None
local_sgtk = None


def get_sg():
    
    if not util.has_shotgun_tank():
        return
    
    global sg
    global local_sgtk
    
    settings = util.get_env('VETALA_SETTINGS')
    
    if settings and sg == None:
        
        
        settings_inst = util_file.SettingsFile()
        settings_inst.set_directory(settings)
        if not util.has_shotgun_tank():
            api_path = settings_inst.get('shotgun_api')
            util.add_to_PYTHONPATH(api_path)
        
        #url = settings_inst.get('shotgun_url')
        name = settings_inst.get('shotgun_name')
        code = settings_inst.get('shotgun_code')
        
        if util.has_shotgun_tank():
            
            import sgtk
            local_sgtk = sgtk
                
                
            try:
                from tank_vendor.shotgun_authentication import ShotgunAuthenticator
                cdm = sgtk.util.CoreDefaultsManager()    
                authenticator = ShotgunAuthenticator(cdm)
                user = authenticator.create_script_user(
                                                        api_script=name,
                                                        api_key=code
                                                        )
                
                sgtk.set_authenticated_user(user)
                
                sg = sgtk.Sgtk.shotgun.fget(1)
                
            except:
                
                try:
                    #for awesome town
                    from bsp.common.db import shotgun_access
                    sg = shotgun_access._getShotgunHandle(name, code)
                    util.show("Using bsp's shotgun_access to get the shotgun handle")
                    #end of for awesome town
                except:
                    util.error('Could not get shotgun api.  Check that your shotgun api script and key code are correct. \nShotgun toolkit might not be installed correctly. \nShotgun may have been initialized to a different project.')
        
        if sg != None:
            util.show('Using Shotgun')
    
    return sg

def get_projects():
    
    sg = get_sg()
    if not sg:
        return
    
    projects = sg.find('Project', [['sg_status','is','Active']], ['name'])
    
    return projects

def get_project_tank(project_name):
    sg = get_sg()
    
    if not sg:
        return
    
    entity = sg.find_one('Project', [['name', 'is',project_name]])
    
    global local_sgtk
    
    if entity:
        
        tank = None
        
        try:
            tank = local_sgtk.sgtk_from_entity('Project', entity['id'])
        except:
            if not util.is_in_maya():
                util.warning('Could not get path for project "%s" using sgtk.sgtk_from_entity. \n Shotgun may have been initialized to a different project.' % project_name)
            if util.is_in_maya():
                util.warning('Could not get path for project %s. Maya was probably loaded with a different project through Shotgun Desktop.' % project_name)
        
        return tank

def get_assets(project_name = None, asset_type = None):
    sg = get_sg()
    if not sg:
        return
    
    filters = []
    
    if project_name:
        filters.append(['project.Project.name', 'is', project_name])
    
    assets = sg.find('Asset', filters, ['code', 'sg_asset_type'])
    
    return assets

def get_asset_steps():
    sg = get_sg()
    if not sg:
        return
    
    filters = []
    
    filters.append(['entity_type', 'is', 'Asset'])
    steps = sg.find('Step', filters, fields = ['code','short_name'])
    
    return steps

def get_asset_step(name):
    
    sg = get_sg()
    if not sg:
        return
    
    filters = []
    
    filters.append(['entity_type', 'is', 'Asset'])
    filters.append(['code', 'is', name])
    
    steps = sg.find_one('Step', filters, fields = ['code','short_name'])
    
    return steps
    

def get_asset_path(project, sg_asset_type, name, step, publish_path = False):
    
    tank = get_project_tank(project)
    
    if not tank:
        return
    
    settings = util.get_env('VETALA_SETTINGS')
    
    settings_inst = util_file.SettingsFile()
    settings_inst.set_directory(settings)
    
    if publish_path:
        code = settings_inst.get('shotgun_asset_publish_template')
    if not publish_path:
        code = settings_inst.get('shotgun_asset_work_template')
    
    step_entity = get_asset_step(step)
    
    
    fields = {}
    fields['sg_asset_type'] = sg_asset_type
    fields['Asset'] = name
    fields['Step'] = step_entity['short_name']
    fields['name'] = name
    fields['version'] = 1
    publish_template =  tank.templates[code]
    
    publish_path = publish_template.apply_fields(fields)
    
    publish_dir = util_file.get_dirname(publish_path)
    
    if not util_file.is_dir(publish_dir):
        fields['Step'] = step_entity['code']
        publish_path = publish_template.apply_fields(fields)
        publish_dir = util_file.get_dirname(publish_path)
    
    return publish_dir

