#!/usr/bin/env python
# vcardtools - library

# TODO
#   * Write doctest for each functions, @see : https://docs.python.org/3/library/doctest.html#module-doctest
#   * Write classes?
#   * Write like reactive (map, filter, etc.)?
#   * Remove all the arguments type checks?

import logging
import re
import warnings
import binascii
from os.path import exists, basename
from collections import OrderedDict
# @see: https://eventable.github.io/vobject/
from vobject import vCard, readComponents
from vobject.vcard import Name
from vobject.base import Component, ContentLine, ParseError

# prevent the import of fuzzywuzzy to raise a UserWarning
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    # @see: https://github.com/seatgeek/fuzzywuzzy
    from fuzzywuzzy.fuzz import token_sort_ratio

# when building a name from an email,
# if the email left part (of '@') startswith one of the following
# then add the domain name as a prefix for the name
EMAIL_USERS_ADD_DOMAIN = (\
    # universal \
    'contact','info','admin','hello','job','question','support','service',\
    # english words \
    'sales','deal','unsubscribe','return',\
    # french words \
    'credit','recrute','desinscription','sav','servicecommercial','relationclient'\
)

# pre-compile regex
REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES = re.compile(' *(\([^)]*\)|\[[^]]*\]) *')
REGEX_ANYTHING_BUT_INDEX = re.compile('(.*)\([0-9]+\)$')
REGEX_ICE = re.compile(r'\b(ICE[0-9]*)\b', re.IGNORECASE)
REGEX_ANY_DASH_OR_UNDERSCORE = re.compile('[_-]')
REGEX_ANY_NUMBER = re.compile('[0-9]')
REGEX_WITHOUT_EXTENSION = re.compile('(.+)\.[a-zA-Z]+$')
REGEX_NAME_IN_EMAIL = re.compile('^ *"(?P<name>[^"]+)" *<[^>]+> *$')
REGEX_EMAIL_WITH_NAME = re.compile('^ *"[^"]+" *<(?P<email>[^>]+)> *$')
REGEX_INVALID_MAIL = re.compile('^nobody[a-z0-9]*@nowhere.invalid$')
REGEX_ONY_NON_ALPHANUM = re.compile('^[ 	]*[^a-zA-Z0-9]*[ 	]*$')

# global options that can be changed by invoking the command line
OPTION_MATCH_ATTRIBUTES = ['names', 'tel_!work', 'email']
OPTION_NO_MATCH_APPROX = False
OPTION_MATCH_APPROX_SAME_FIRST_LETTER = True
OPTION_MATCH_APPROX_STARTSWITH = False
OPTION_MATCH_APPROX_MIN_LENGTH = 5
OPTION_MATCH_APPROX_MAX_DISTANCE = range(-3, 3)
OPTION_MATCH_APPROX_RATIO = 100
OPTION_UPDATE_GROUP_KEY = True
OPTION_FRENCH_TWEAKS = False

SINGLE_INSTANCE_PROPERTIES = {'prodid', 'rev', 'uid'}

def add_attributes(attributes, a):
    """
    Return void

    Add an attribute a to the attributes list,
    checking if the attribute is not already there,
    and if it is the case, only append missing parameters

    attributes -- the list of attributes
    a          -- the attribute to add
    """

    if not isinstance(attributes, list):
        raise TypeError("parameter 'attributes' must be a list (type: '" + str(type(attributes)) + "')")
    if a is None:
        raise TypeError("trying to add an undefined attribute")
    # TODO: check the attribute type of instance

    # note: normalization should have been done before

    # search for existing attribute with the same value
    existing = False
    for attr in attributes:
        if attr.value == a.value:

            # append parameters
            if hasattr(a, 'params') and a.params:
                if not hasattr(attr, 'params'): # should not happen
                    raise RuntimeError("Attribute '" + a.name + "' has no key 'params'")
                for p_name, p_value in a.params.items():
                    if p_value:
                        if not p_name in attr.params:
                            setattr(attr, p_name + '_param', p_value)
                            logging.debug("\t\t\tadded param '%s[%s] to '%s'", p_name, p_value, a.value)
                        else:
                            p_values = getattr(attr, p_name + '_paramlist')
                            for pv in p_value:
                                if not pv in p_values:
                                    p_values.append(pv)
                                    logging.debug("\t\t\tadded param '%s[%s] to '%s'", p_name, pv, a.value)
            existing = True
            break
    # new attribute
    if not existing:
        attributes.append(a)
        logging.debug("\t\t\tadded '%s'", a.value)


def collect_attributes(vcards):
    """
    Return a dict containing all attributes collected from the vCards

    Format is attributes_dict[attribute_name] = attribute_value
    attribute_value can be a string, a ContentLine or a list of both mixed

    vcards -- a dict or list of vcards
    """

    if not isinstance(vcards, dict):
        if not isinstance(vcards, list):
            raise TypeError("parameter 'vcards' must be a dict or list (type: '" + str(type(vcards)) + "')")

    # build a lists of ordered vcards
    if isinstance(vcards, dict):
        vcards_sorted = [v for v in vcards.values()]
    elif isinstance(vcards, list):
        vcards_sorted = vcards.copy()

    logging.debug("Collecting attributes ...")
    attributes = {}
    # for every vCard in the list
    for i in range(len(vcards_sorted)):
        vcard1 = vcards_sorted[0]
        logging.debug("\tprocessing vcard '%s'", vcard1.fn.value)

        # for every attribute of the vCard
        for c1 in vcard1.getChildren():
            a1 = c1.name.lower()

            if a1 == 'version':
                logging.debug("\t\tskipping VERSION attribute")
                continue

            # if the attribute has not already been collected
            if not a1 in attributes:

                logging.debug("\t\tcollecting attribute '%s'", a1)

                # collect all vCards values for this attribute
                for vcard2 in vcards_sorted:
                    if hasattr(vcard2, a1):
                        attrlist = getattr(vcard2, a1 + '_list')
                        if attrlist:
                            if a1 not in attributes:
                                attributes[a1] =  []
                            for a in attrlist:
                                add_attributes(attributes[a1], a)
                        
        # prevent the vcard from being processed again
        del vcards_sorted[0]

    return attributes


def build_name_from_email(email):
    """ Return a string containing a name built from an email """

    if not isinstance(email, str):
        raise TypeError("parameter 'email' must be a string (type: '" + str(type(email)) + "')")
    
    # don't use a thunderbird invalid email
    if email.lower().strip().endswith('nowhere.invalid'):
        raise ValueError("Trying to extract a name from a Thunderbird invalid email (" + email + ")")

    # split both side of the @
    email_user, email_domain = email.strip().rsplit("@")
    # remove any dash or underscore, or any number
    name = REGEX_ANY_DASH_OR_UNDERSCORE.sub(' ', REGEX_ANY_NUMBER.sub('', email_user))
    # specific cases where we add the domain as a prefix (without the extension)
    if name.lower().startswith(EMAIL_USERS_ADD_DOMAIN):
        name = REGEX_WITHOUT_EXTENSION.sub('\\1', REGEX_ANY_DASH_OR_UNDERSCORE.sub(' ', email_domain)) + " - " + name
    # remove dots
    name = name.replace('.', ' ')
    # return a sanitized name
    return sanitize_name(name)


def sanitize_name(name):
    """
    Return a name string with some sanitizing and formatting done.

    Sanitizing is:
    - removing ICE (In Case of Emergency)
    - removing dots
    - replacing double spaces by one
    - triming edge spaces
    - capitalizing the first letter of each word and lowercase the rest
    """
    if not isinstance(name, str):
        raise TypeError("parameter 'name' must be a string (type: '" + str(type(name)) + "')")
    
    # remove ICE (In Case of Emergency)
    # remove dots
    # replace double spaces by one
    # trim side spaces
    # capitalize the first letter of each word and lowercase the rest
    sanitized = REGEX_ICE.sub('', name).replace('.', ' ').replace('  ', ' ').replace('  ', ' ').strip().title()
    # remove data in parentheses/braces if they are equals to the outer data
    if REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(name):
        inner = re.sub(r'[\(\)\[\]]', '', ' '.join(REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(name).groups()).strip()).title()
        outer = REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.sub('', name).strip().title()
        # match even words in a different order
        if inner == outer or token_sort_ratio(inner, outer) == 100:
            sanitized = outer
    return sanitized


def length_without_parenthese_or_braces(string):
    """ Return the length with anything between parentheses or braces removed """

    if not isinstance(string, str):
        raise TypeError("parameter 'string' must be a string (type: '" + str(type(string)) + "')")
    
    return len(REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.sub('', string))


def length_without_index(string):
    """ Return the length with the index number in parentheses removed """

    if not isinstance(string, str):
        raise TypeError("parameter 'string' must be a string (type: '" + str(type(string)) + "')")
    
    return len(REGEX_ANYTHING_BUT_INDEX.sub('\\1', string))


def build_formatted_name(name):
    """
    Return a dict with the following keys: 'family', 'given', and optionaly 'suffix'.
    The dict return should be used to build a n.value.

    name -- a string
    """

    if not isinstance(name, str):
        raise TypeError("parameter 'name' must be a string (type: '" + str(type(name)) + "')")
    
    name_suffix = None

    # the name has parentheses or braces that has to be put as a suffix
    if REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(name):
        name_suffix = ','.join(REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(name).groups()).strip()
        name = REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.sub('', name)

    # the name has been structured properly to be splitted
    if ' - ' in name:
        name_splitted = name.split(' - ')
        name_family = name_splitted[0]
        del name_splitted[0]
    # french tweak to handle particle names
    elif OPTION_FRENCH_TWEAKS and ' de ' in name.lower():
        name_splitted = name.lower().split(' de ')
        name_family = 'De ' + name_splitted[0]
        del name_splitted[0]
    # normal cases
    else:
        name_splitted = name.split(' ')
        name_family = name_splitted[-1]
        name_splitted.pop()
    name_given = ' '.join(name_splitted)
    if name_suffix:
        return Name(family=name_family, given=name_given, suffix=name_suffix)
    return Name(family=name_family, given=name_given)


def set_name(attributes):
    """
    Return void

    Collect names values from 'fn' and 'n' fields and the filenames in key 'names'.
    Select he longuest one.
    Remove keys 'fn', 'n' and 'names'
    Rebuild field 'fn' and 'n' from the selected name

    attributes -- a dict of attributes
    """

    if not isinstance(attributes, dict):
        raise TypeError("parameter 'attributes' must be a dict (type: '" + str(type(attributes)) + "')")

    logging.debug("Setting name ...")

    # collect names
    logging.debug("\tcollecting names ...")
    available_names = []
    if 'fn' in attributes:
        for n in attributes['fn']:
            name = sanitize_name(n.value)
            if not name in available_names:
                available_names.append(name)
    if 'n' in attributes:
        for n in attributes['n']:
            name = sanitize_name(str(n.value))
            if not name in available_names:
                available_names.append(name)
    if 'email' in attributes:
        for m in attributes['email']:
            n_matches = REGEX_NAME_IN_EMAIL.match(m.value.strip())
            if n_matches:
                name = sanitize_name(n_matches.group('name'))
                if not name in available_names:
                    available_names.append(name)
    logging.debug("\tnames collected:")
    for n in available_names:
        logging.debug("\t\t'%s'", n)

    # select the most relevant name
    selected_name = select_most_relevant_name(available_names)

    # delete names attributes
    del attributes['fn']
    del attributes['n']

    # rebuild them from the name selected
    attributes['fn'] = selected_name
    attributes['n'] = build_formatted_name(selected_name)


def select_most_relevant_name(names):
    """ Return the longuest name (without parenthese or braces). """

    if not isinstance(names, list):
        raise TypeError("parameter 'names' must be a list (type: '" + str(type(names)) + "')")
    if not names:
        raise ValueError("Trying to select a name from an empty list of names")

    logging.debug("\t\tselecting the most relevant name from:")
    logging.debug("\t\t\t%s", ', '.join(names))
    selected_name = None
    longuest_length = 0
    pos = 0
    for n in names:
        if not n:
            raise TypeError("parameter 'names[" + str(pos) + "]' is undefined")
        length = length_without_parenthese_or_braces(n)
        # longuer
        if length > longuest_length:
            longuest_length = length
            selected_name = n
        # equal length
        elif length == longuest_length:
            # longuer without index
            if length_without_index(n) > length_without_index(selected_name):
                selected_name = n
            # equal length without index
            elif length_without_index(n) == length_without_index(selected_name):
                # if no index and the selected has one
                if length_without_index(n) == len(n) \
                and length_without_index(selected_name) != len(selected_name):
                    longuest_length = length
                    selected_name = n
        pos += 1
    logging.debug("\t\tselected: '%s'", selected_name)

    if not selected_name: # should not happen
        raise RuntimeError("Failed to select a name")
    elif '=' in selected_name:
        raise RuntimeError("Invalid selected name '" + selected_name + "' (contains an equals sign: maybe an undecoded string)")

    return selected_name 


def build_vcard(attributes):
    """
    Return a vcard build from the attributes list

    attributes -- a dict of attributes
    """
    
    if not isinstance(attributes, dict):
        raise TypeError("parameter 'attributes' must be a dict (type: '" + str(type(attributes)) + "')")
    
    logging.debug("Building vcard ...")
    vcard = vCard()

    defined_single_instance_properties = set()

    for a_name, a in attributes.items():
        #logging.debug("\tprocessing '%s' -> '%s'", a_name, a)
        if a:
            if a_name == 'n':
                if hasattr(a, 'suffix'):
                    vcard.add('n').value = Name( \
                        family=a.family, \
                        given=a.given, \
                        suffix=a.suffix \
                    )
                else:
                    vcard.add('n').value = Name(\
                        family=a.family, \
                        given=a.given \
                    )
                logging.debug("\t%s: %s", a_name, str(vcard.n.value).replace(' ', '').strip())
            elif a_name == 'org':
                if not isinstance(a, list):
                    raise RuntimeError("'org' collected attributes should be a list, '" + str(type(a)) + "' found")
                org = vcard.add('org')
                org.value = []
                for o in a:
                    if isinstance(o, str):
                        org.value.append(o)
                    elif isinstance(o, ContentLine):
                        org.value += o.value
                    else:
                        raise RuntimeError("'org' value should be string or ContentLine, '" + str(type(o)) + "' found")
                logging.debug("\t%s: %s", a_name, vcard.org.value)
            else:
                if isinstance(a, str):
                    vcard.add(a_name).value = a
                    logging.debug("\t%s: %s", a_name, a)
                elif isinstance(a, ContentLine):
                    item_added = vcard.add(a_name)
                    logging.debug("\t%s: %s", a_name, str(a.value))
                    item_added.value = a.value
                    if hasattr(a, 'params') and a.params:
                        for p_name, p_value in a.params.items():
                            setattr(item_added, p_name + '_param', p_value)
                            logging.debug("\t\twith param '%s': '%s'", p_name, p_value)
                else:
                    for a_item in a:
                        if a_item:
                            if isinstance(a_item, str):
                                vcard.add(a_name).value = a_item
                                logging.debug("\t%s: %s", a_name, a_item)
                            elif isinstance(a_item, ContentLine):
                                if a_name in SINGLE_INSTANCE_PROPERTIES:
                                    if a_name in defined_single_instance_properties:
                                        continue
                                    else:
                                        defined_single_instance_properties.add(a_name)
                                item_added = vcard.add(a_name)
                                logging.debug("\t%s: %s", a_name, a_item.value)
                                item_added.value = a_item.value
                                if hasattr(a_item, 'params') and a_item.params:
                                    for p_name, p_value in a_item.params.items():
                                        setattr(item_added, p_name + '_param', p_value)
                                        logging.debug("\t\twith param '%s': '%s'", p_name, p_value)
    logging.debug("vcard built:\n%s", vcard.serialize())
    return vcard


def close_parentheses_or_braces(string):
    """
    Add a missing parenthese or brace to close one open
    
    If the paranethese or brace is at the begining of the string,
    it will be removed instead. That's because if it was closed with a pair
    at the end of the string, the whole string will be contained in
    parentheses or braces which will be ignored in the processing.
    """
    if '(' in string and not ')' in string:
        if re.match('^ *\(', string):
            string = re.sub('^ *\(', '', string)
        else:
            string += ')'
    elif '[' in string and not ']' in string:
        if re.match('^ *\[', string):
            string = re.sub('^ *\[', '', string)
        else:
            string += ']'
    return string


def collect_vcard_names(vcard):
    """ Collect all vcard possible names in fields 'fn', 'n' and 'email' """
    if not isinstance(vcard, Component):
        raise TypeError("parameter 'vcard' must be a vobject.base.Component (type: '" + str(type(vcard)) + "')")

    # collect names
    logging.debug("\tcollecting names %s ...", "for '" + vcard.fn.value + "'" if hasattr(vcard, 'fn') else '')
    available_names = []
    for k in ['fn', 'n']:
        if hasattr(vcard, k):
            for n in getattr(vcard, k + '_list'):
                value = close_parentheses_or_braces(str(n.value).strip())
                if not REGEX_ONY_NON_ALPHANUM.match(value):
                    if '@' in value:
                        name = build_name_from_email(value)
                        if not name in available_names:
                            available_names.append(name)
                            logging.debug("\t\tadding '%s' from built email for '%s'", name, k)
                    else:
                        name = sanitize_name(value)
                        if not name in available_names:
                            available_names.append(name)
                            logging.debug("\t\tadding '%s' from '%s'", name, k)
                else:
                    logging.debug("\t\tskipping non-alphanum name value: '%s'", value)
    if hasattr(vcard, 'email'):
        for m in vcard.email_list:
            # not a thunderbird invalid email
            if not m.value.lower().strip().endswith('nowhere.invalid'):
                n_matches = REGEX_NAME_IN_EMAIL.match(m.value)
                if n_matches:
                    name = sanitize_name(n_matches.group('name'))
                    if not name in available_names:
                        available_names.append(name)
                        logging.debug("\t\tadding '%s' from 'email'", name)

    # no name found, but there is an email : build a name from it
    if not available_names and hasattr(vcard, 'email'):
        for m in vcard.email_list:
            name = build_name_from_email(m.value)
            if not name in available_names:
                available_names.append(name)
                logging.debug("\t\tadding '%s' from built 'email'", name)

    # no name found, but there is an org : use it as name
    if not available_names and hasattr(vcard, 'org'):
        for o in vcard.org_list:
            if o.value:
                if isinstance(o.value, list):
                    for oo in o.value:
                        if not REGEX_ONY_NON_ALPHANUM.match(oo.strip()):
                            name = sanitize_name(oo)
                            if not name in available_names:
                                available_names.append(name)
                                logging.debug("\t\tadding '%s' from 'org' list", name)
                elif not REGEX_ONY_NON_ALPHANUM.match(o.value.strip()):
                    name = sanitize_name(o.value)
                    if not name in available_names:
                        available_names.append(name)
                        logging.debug("\t\tadding '%s' from 'org'", name)

    # no name found, but there is a tel : build a name from it
    if not available_names and hasattr(vcard, 'tel'):
        name = 'tel_' + str(vcard.tel.value).strip()
        if not name in available_names:
            available_names.append(name)
            logging.debug("\t\tadding '%s' from built 'tel'", name)

    # what we have found
    logging.debug("\tnames collected:")
    for n in available_names:
        logging.debug("\t\t'%s'", n)
    return available_names


def write_vcard_to_file(vcard, file_path):
    """
    Return void.

    Serialize the vcard then write it to the specified file.

    vcard     -- the vcard
    file_path -- the file path
    """

    if not isinstance(vcard, Component):
        raise TypeError("parameter 'vcard' must be a vobject.base.Component (type: '" + str(type(vcard)) + "')")
    if not isinstance(file_path, str):
        raise TypeError("parameter 'file_path' must be a string (type: '" + str(type(file_path)) + "')")

    # serialize the vcard to produce a string content
    file_content = vcard.serialize()

    # check if the file already exists
    if exists(file_path): # should not happen
        raise RuntimeError("Failed to write vcard to file '" + file_path + "' : file already exists.")

    # open file in write mode
    with open(file_path, 'w') as c_file:
        try:
            # write to it
            c_file.write(file_content)
            logging.debug("Writen vCard file '%s'", file_path)
        except OSError as e:
            logging.error("Failed to write file '%s'", file_path)
            logging.error(e)
            raise
    logging.debug("\tWriten vCard to file '%s'", file_path)


def normalize(vcard, selected_name, \
  do_not_overwrite_names=False, \
  move_name_parentheses_or_braces_to_note=False, \
  do_not_remove_name_in_email=False \
):
    """
    Return void.

    Normalize a vcard.

    Normalizing consist of :
    - removing 'version' attribute
    - overwriting names attributes 'fn' and 'n' with the one specified (if not disabled by option)
    - adding missing names attributes 'fn' and 'n'
    - moving name's content inside parentheses or braces into the note attribute (if enabled by option)
    - removing thunderbird invalid email form emails
    - removing name in email (if not disabled by option)
    - removing space in tels numbers
    - replacing '+33' by '0' in tels numbers (if french tweaks are enabled)

    Arguments:
    vcard         -- the vcard
    selected_name -- a name for the vcard (used to overwrite existing ones)

    Options:
    do_not_overwrite_names
    move_name_parentheses_or_braces_to_note
    do_not_remove_name_in_email

    Global options used:
        OPTION_FRENCH_TWEAKS
    """
    if not isinstance(vcard, Component):
        raise TypeError("parameter 'vcard' must be a vobject.base.Component (type: '" + str(type(vcard)) + "')")
    if not isinstance(selected_name, str):
        raise TypeError("parameter 'selected_name' must be a string (type: '" + str(type(selected_name)) + "')")

    # remove vCard version
    if hasattr(vcard, 'version'):
        del vcard.version
        logging.debug("\t\tremoved VERSION attribute")

    # overwrite names with the selected one
    if not do_not_overwrite_names:
        # remove all name fields
        if hasattr(vcard, 'fn'):
            del vcard.fn
            logging.debug("\t\tremoved 'fn' attribute")
        if hasattr(vcard, 'n'):
            del vcard.n
            logging.debug("\t\tremoved 'n' attribute")

    # add missing required name fields 'fn' and 'n'
    if not hasattr(vcard, 'fn'):
        vcard.add('fn').value = selected_name
        #vcard.add('fn').value = REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.sub('', selected_name).strip()
        logging.debug("\t\tadded missing 'fn' attribute with value '%s'", vcard.fn.value)
    if not hasattr(vcard, 'n'):
        vcard.add('n').value = build_formatted_name(selected_name)
        logging.debug("\t\tadded missing  'n' attribute with value '%s'", str(vcard.n.value).replace('  ', ' ').strip())

    # move name's content inside parentheses or braces into the note attribute
    if move_name_parentheses_or_braces_to_note:
        for k in ['fn', 'n']:
            for n in getattr(vcard, k + '_list'):
                value = close_parentheses_or_braces(str(n.value).replace('  ', ' ').strip())
                if REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(value):
                    logging.debug("\t\tname['%s'] '%s' has parentheses or braces", k, value)
                    inner = re.sub(r'[\(\)\[\]]', '', ' '.join(REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.search(value).groups()).strip())
                    outer = REGEX_ANYTHING_BETWEEN_PARENTHESES_OR_BRACES.sub('', value).strip()
                    if k == 'n':
                        n.value = build_formatted_name(outer)
                        logging.debug("\t\tname['%s'] is now: '%s'", k, str(n.value).replace('  ', ' ').strip())
                    else:
                        n.value = outer
                        logging.debug("\t\tname['%s'] is now: '%s'", k, n.value)
                    if hasattr(vcard, 'note'):
                        vcard.note.value += '\n' + inner
                    else:
                        vcard.add('note').value = inner
                    logging.debug("\t\t'note' is now: '%s'", vcard.note.value)

    # normalize email
    if hasattr(vcard, 'email') and vcard.email_list:
        number_of_email = len(vcard.email_list)
        i = 0
        while i < number_of_email:
            m = vcard.email_list[i]
            m.value = m.value.strip().lower()
            # filter out thunderbird invalid email
            if m.value.endswith('@nowhere.invalid'):
                del vcard.email_list[i]
                number_of_email -= 1
            # normal email
            else:
                m_match = REGEX_EMAIL_WITH_NAME.match(m.value)
                if m_match and not do_not_remove_name_in_email:
                    m.value = ''.join(m_match.group('email'))
                i += 1
        if len(vcard.email_list) == 0:
            del vcard.email_list

    
    # normalize tel
    if hasattr(vcard, 'tel') and vcard.tel_list:
        for t in vcard.tel_list:
            t.value = t.value.strip().replace(' ', '')
            if OPTION_FRENCH_TWEAKS:
                # re-localize
                if t.value.startswith('+33'):
                    t.value = t.value.replace('+33', '0')

    # TODO: strip all values


def get_vcards_from_files(files, \
  do_not_fix_and_convert=False, \
  do_not_overwrite_names=False, \
  move_name_parentheses_or_braces_to_note=False, \
  do_not_remove_name_in_email=False \
):
    """
    Return a dict of vobject.vcard.

    vCards will be normalized.

    arguments:
    files -- a list of the vcf/vcard files to read from

    options:
    do_not_overwrite_names        -- do not overwrite existing field names with the one selected
    do_not_remove_name_from_email -- do not remove name from email (like: "John Doe" <john@doe.com>)
    """

    if not isinstance(files, list):
        raise TypeError("parameter 'files' must be a list (type: '" + str(type(files)) + "')")

    # read all files
    logging.info("Reading/parsing individual vCard files ...")
    vcards = {}
    file_names_max_length = max(map(lambda x: len(basename(x)), files))
    logging.debug("file names max length: %d", file_names_max_length)
    for f_path in files:
        f_name = basename(f_path)

        # read the file content and fix it + converting vCard from 2.1 to 3.0
        if not do_not_fix_and_convert:
            content = fix_and_convert_to_v3(f_path)
        else:
            with open(f_path, 'rU') as vfile:
                content = vfile.read()

        try:
            # parse the content and create a vcard list
            vcard_list = readComponents(content)

            # add the vcards to the global vcards list
            count = 0
            for vcard in vcard_list:
                count += 1

                # collect names
                available_names = collect_vcard_names(vcard)

                # select the most relevant name
                selected_name = select_most_relevant_name(available_names)

                # normalize the fields
                normalize(vcard, selected_name, do_not_overwrite_names, move_name_parentheses_or_braces_to_note, do_not_remove_name_in_email)

                # force the full parsing of the vcard to prevent further crash
                try:
                    vcontent = vcard.serialize()
                except TypeError as e:
                    logging.error("Failed to parse vCard [%d] '%s' of file '%s'", count, selected_name, f_path)
                    logging.error(e)
                    raise

                # increment the name if already used
                if selected_name in vcards:
                    index = 0
                    name_indexed = selected_name
                    while name_indexed in vcards:
                        index += 1
                        name_indexed = selected_name + "(" + str(index) + ")"
                    selected_name = name_indexed
                
                # add the card to the list
                vcards[selected_name] = vcard

            # sum up the parsing for that file
            logging.info(('\t{0:<' + str(file_names_max_length) + '} : {1:>5} vCards parsed').format(f_name, count)) 

        # parsing failure (advenced)
        except (TypeError, UnicodeDecodeError, binascii.Error) as e:
            logging.error("Failed to parse vCard [%d] (after '%s') of file '%s'", count, selected_name, f_path)
            logging.error(e)
            raise

        # parsing failure (raw)
        except ParseError as e:
            logging.error("Failed to parse vCard [%d] of file '%s'", count, f_path)
            logging.error(e)
            raise

    return vcards


def deduplicate(vcard):
    """ Remove duplicated fields and merge their parameters """

    if not isinstance(vcard, Component):
        raise TypeError("parameter 'vcard' must be a vobject.base.Component (type: '" + str(type(vcard)) + "')")

    # collect attributes for all vCards
    attributes = collect_attributes([vcard])
    # select a name (filter 'fn' and 'n' attributes)
    set_name(attributes)
    # save the remaining attributes to the merged vCard
    return build_vcard(attributes)


def fix_and_convert_to_v3(file_path):
    """
    Return a string containing the file content fixed and converted to vcard 3.0

    Fixes:
    * remove DOS CRLF and Apple CR
    * concatenation of multilines quoted-printable value (not the binary data)
    * convert keys to upper case
    * remove double QUOTED-PRINTABLE
    * factorize TYPE parameters
    * add PHOTO 'VALUE=URI' when JPEG without encoding specified
    * add 'CHARSET=UTF-8' when QUOTED-PRINTABLE without any charset

    Convertion from 2.1 to 3.0 :
    * replace 'QUOTED-PRINTABLE' with 'ENCODING=QUOTED-PRINTABLE'
    * replace 'ENCODING=BASE64' with 'ENCODING=b'
    * add prefix 'TYPE=' for following parameters :
        PGP,PNG,JPEG,OGG,INTERNET,PREF,HOME,WORK,MAIN,CELL,FAX,VOICE
    """

    if not isinstance(file_path, str):
        raise TypeError("parameter 'file_path' must be a string (type: '" + str(type(file_path)) + "')")

    # read/parse the whole file
    logging.debug("Reading/parsing the VCF file '%s' ...", file_path)
    lines = []
    last_line = None
    line_endings = None
    started_quoted_printable = False
    with open(file_path, 'rU') as vfile:

        # read line by line
        for line in vfile:
            logging.debug("\t* processing line: %s", line.replace('\n', ''))

            if line_endings != repr(vfile.newlines):
                line_endings = repr(vfile.newlines)
                logging.debug("\tfound new line endings: %s", str(line_endings))

            # remove DOS CRLF and Apple LF
            #line_unix = re.sub(r'\r(?!\n)|(?<!\r)\n', '\n', line)
            line_unix = line
            if '\r\n' in line_unix:
                line_unix = line_unix.replace('\r\n', '\n')
                logging.debug("\tfound DOS line (converted to unix)")
            if '\r' in line_unix:
                line_unix = line_unix.replace('\r', '\n')
                logging.debug("\tfound Apple line (converted to unix)")
            line = line_unix.replace('\n', '')

            # save the previous line
            if last_line:
                logging.debug("\tprevious line was not saved")

                # quoted-printable multilines value hack :
                # add this line to the previous one (and strip it)
                if started_quoted_printable \
                and not re.match(r'^([^: ]+):.*', line):
                    logging.debug("\tmultiline value hack (joining this line with the previous)")
                    if last_line.replace('\n', '')[-1:] == '=':
                        last_line = re.sub('=$', '', last_line.replace('\n', '')) + '\n'
                    last_line = last_line.replace('\n', '') + line.strip() + '\n'
                    logging.debug("\tconcatened: '%s'", line.strip())
                    logging.debug("\t")
                    continue
                
                # save the previous line
                else:
                    lines.append(last_line)
                    last_line = None
                    started_quoted_printable = False
                    logging.debug("\tsaving the previous line")

            new_line = line

            # its a BEGIN or END line
            if re.match(r'^(BEGIN|END):VCARD$', new_line, re.IGNORECASE):
                logging.debug("\tline is a BEGIN or END line")
                new_line = new_line.upper()

            # its a key:value line
            elif re.match(r'^([^: ]+):.*', new_line):
                logging.debug("\tline is a key:value")

                # convert keys to upper case
                key_part = new_line.rsplit(':')[0].upper()
                logging.debug("\tkey part: '%s'", key_part)
                rest_part = re.sub(r'^([^:]+):', '', new_line)
                logging.debug("\trest part: '%s'", rest_part)
                new_line = key_part + ':' + rest_part
                logging.debug("\tbuilt new line: %s", new_line)

                # there are multiple fields
                if ';' in key_part:
                    logging.debug("\tthere are multiple fields")

                    # remove double QUOTED-PRINTABLE
                    if 'QUOTED-PRINTABLE;QUOTED-PRINTABLE' in key_part:
                        key_part = key_part.replace('QUOTED-PRINTABLE;QUOTED-PRINTABLE', 'QUOTED-PRINTABLE')
                        logging.debug("\tremoved double QUOTED-PRINTABLE")
                        logging.debug("\tkey part: '%s'", key_part)

                    # prefix every known type with 'TYPE='
                    new_key_part = re.sub(r';(PGP|PNG|JPEG|OGG|INTERNET|PREF|HOME|WORK|MAIN|CELL|FAX|VOICE)', ';TYPE=\\1', key_part)
                    logging.debug("\tnew key part: %s", new_key_part)

                    # the key part has at least one 'TYPE='
                    if 'TYPE=' in new_key_part:
                        key_value = re.sub(r'^([^;]+);.*', '\\1', key_part)
                        type_list = []
                        rest_list = []

                        for field in re.sub(r'^([^;]+);', '', new_key_part).split(';'):
                            # collect the TYPE fields
                            if field.startswith('TYPE='):
                                type_list.append(re.sub(r'^TYPE=', '', field))
                            # collect others fields
                            else:
                                if field in ['ENCODING=BASE64', 'ENCODING=B']:
                                    field = 'ENCODING=b'
                                elif field == 'QUOTED-PRINTABLE':
                                    field = 'ENCODING=QUOTED-PRINTABLE'
                                    logging.debug("\tconverted 'QUOTED-PRINTABLE' to 'ENCODING=QUOTED-PRINTABLE'")
                                rest_list.append(field)

                        # add PHOTO 'VALUE=URI' when JPEG if required
                        if 'JPEG' in type_list and not 'ENCODING=b' in rest_list \
                        and not 'VALUE=URI' in rest_list:
                            logging.debug("\tadded PHOTO 'VALUE=URI'")
                            rest_list.append('VALUE=URI')

                        # add 'CHARSET=UTF-8' when 'ENCODING=QUOTED-PRINTABLE' if required
                        if 'ENCODING=QUOTED-PRINTABLE' in rest_list \
                        and not 'CHARSET=' in ','.join(rest_list):
                            logging.debug("\tadded 'CHARSET=UTF-8'")
                            rest_list.append('CHARSET=UTF-8')

                        # build the new line
                        new_line = "{0};TYPE={1}{2}:{3}".format(key_value, ','.join(type_list), ';' + ';'.join(rest_list) if rest_list else '', rest_part)
                        logging.debug("\tbuilt new line: %s", new_line)

                    # the key part has no 'TYPE='
                    else:
                        if 'QUOTED-PRINTABLE' in new_key_part:
                            new_key_part = new_key_part.replace(';QUOTED-PRINTABLE', ';ENCODING=QUOTED-PRINTABLE')
                            logging.debug("\tconverted 'QUOTED-PRINTABLE' to 'ENCODING=QUOTED-PRINTABLE'")
                            if not 'CHARSET=' in new_key_part:
                                new_key_part = new_key_part.replace('=QUOTED-PRINTABLE', '=QUOTED-PRINTABLE;CHARSET=UTF-8')
                                logging.debug("\tadded 'CHARSET=UTF-8'")

                        new_line = new_key_part + ':' + rest_part
                        logging.debug("\tbuilt new line: %s", new_line)

                    # starting a quoted-printable line
                    if 'ENCODING=QUOTED-PRINTABLE' in new_line:
                        started_quoted_printable = True

            # last_line is the new_line (will be saved at the next iteration)
            last_line = new_line + '\n'
            logging.debug("\t")

        # save the last line if needed
        if last_line:
            lines.append(last_line)
            last_line = None
            logging.debug("\tlast line saved")
                
    # produce a file content
    logging.debug("Producing file content (joining lines)")
    return ''.join(lines)


def is_a_mobile_phone(number):
    """ Return True if the number is a number for a mobile phone """

    if not isinstance(number, str):
        raise TypeError("parameter 'number' must be a string (type: '" + str(type(number)) + "')")

    return number.startswith(('06','07')) # This is for France, I don't know other country


def collect_values(vcard, *keys):
    """
    Return a set of uniques values collected for the attributes keys specified.

    arguments:
    vcard -- the vcard to read values from
    *keys -- an attribute key,
             can be a key 'key',
             a key and a type 'key_type',
             or an alias like:
                'mobiles': 'tel' filtered by number
                'names': that combine 'fn' and 'n' values into the same set

    examples:
        collect_values(vcard, 'fn', 'n') to get values for attributes 'fn' and 'n'
        collect_values(vcard, 'email_home') to get values for attribute 'email' and type 'home'
        collect_values(vcard, 'mobiles') to get 'tel' values filtered by is_a_mobile_number()
    """

    if not isinstance(vcard, Component):
        raise TypeError("parameter 'vcard' must be a vobject.base.Component (type: '" + str(type(vcard)) + "')")
    if not isinstance(keys, tuple):
        raise TypeError("parameter 'keys' must be a tuple (type: '" + str(type(keys)) + "')")

    values = []

    # names alias
    if 'names' in keys:
        if not 'fn' in keys:
            keys += ('fn',)
        if not 'n' in keys:
            keys += ('n',)

    # collect values
    for k in keys:
        # key filtered by type
        if '_' in k:
            k_name, k_type = k.rsplit("_")
            if hasattr(vcard, k_name):
                values.extend(filter_values_by_param(vcard, k_name, "TYPE", k_type))
        # 'mobiles' alias
        elif k == 'mobiles':
            if hasattr(vcard, 'tel'):
                for t in vcard.tel_list:
                    if t and is_a_mobile_phone(str(t.value).strip()):
                        values.append(str(t.value).strip())
        # normal case (not processing 'names', because it have been replace with 'fn' and 'n')
        elif k != 'names':
            if hasattr(vcard, k):
                for v in getattr(vcard, k + "_list"):
                    if v and v.value:
                        if k == 'n':
                            values.append(re.sub(' +', ' ', str(v.value)).strip())
                        elif k == 'org' and isinstance(v.value, list):
                            for vv in v.value:
                                values.append(vv.strip())
                        else:
                            values.append(str(v.value).strip())
    return set(values)


def filter_values_by_param(vcard, key, param_key, param_value):
    """
    Return a list of values collected for vcard and filtered by parameters.

    arguments:
    vcard       -- the vcard to read from
    key         -- the attribute key to collect values for
    param_key   -- the name of the parameter to filter by
                   if starting by '!', means exclude those values
    param_value -- the value of the parameter
    """

    fvalues = []

    # excluding
    exclude = False
    if param_value.startswith('!'):
        param_value = param_value[1:]
        exclude = True

    # force upper case value
    param_value = param_value.upper()

    if hasattr(vcard, key) and getattr(vcard, key + "_list"):

        # for each values for that key
        for v in getattr(vcard, key + "_list"):

            # define if we collect it or not
            append = False
            if str(v.params.get(param_key)).upper() == "['" + param_value + "']":
                if not exclude:
                    append = True
            elif exclude:
                append = True

            # appending the value
            if append:
                if key == 'n':
                    fvalues.append(re.sub(' +', ' ', str(v.value)).strip())
                elif key == 'org' and isinstance(v.value, list):
                    for vv in v.value:
                        fvalues.append(vv.strip())
                else:
                    fvalues.append(str(v.value).strip())

    return fvalues


def reverse_words(string):
    """
    Return a string with words in the reverse order.

    Tryes to use name comprehension to split smartly by family name.
    Else it default to a simple reversing.
    """
    reverseName = build_formatted_name(string)
    return reverseName.family + ' ' + reverseName.given


def match_approx(a, b):
    """
    Return True if 'a' match 'b'.

    Use fuzzy matching according to OPTIONS.

    Global options used:
        OPTION_MATCH_APPROX_SAME_FIRST_LETTER
        OPTION_MATCH_APPROX_STARTSWITH
        OPTION_MATCH_APPROX_MIN_LENGTH
        OPTION_MATCH_APPROX_MAX_DISTANCE
        OPTION_MATCH_APPROX_RATIO
    """
    if not isinstance(a, str):
        raise TypeError("parameter 'a' must be a string (type: '" + str(type(a)) + "')")
    if not isinstance(b, str):
        raise TypeError("parameter 'b' must be a string (type: '" + str(type(b)) + "')")

    # safe approximate matching
    if OPTION_MATCH_APPROX_RATIO == 100:
        score = token_sort_ratio(a, b)
        if score == 100:
            logging.debug("\t'%s' ~ '%s' (score: 100)", a, b)
            return True

    # ensure a minimal length when doing unsafe approximate match
    if len(a) > OPTION_MATCH_APPROX_MIN_LENGTH and len(b) > OPTION_MATCH_APPROX_MIN_LENGTH:

        # build reversed words names
        if OPTION_MATCH_APPROX_SAME_FIRST_LETTER or OPTION_MATCH_APPROX_STARTSWITH:
            a_reversed = reverse_words(a)
            b_reversed = reverse_words(b)

        # ensure the same first letter (reverse is ok too), if required
        if not OPTION_MATCH_APPROX_SAME_FIRST_LETTER \
        or a[:1].lower() == b[:1].lower() \
        or a[:1].lower() == b_reversed[:1].lower() \
        or a_reversed[:1].lower() == b[:1].lower():

            # "startswith" comparizon, with a maximum distance
            if OPTION_MATCH_APPROX_STARTSWITH \
            and len(a) - len(b) in OPTION_MATCH_APPROX_MAX_DISTANCE:
                if a.startswith(b):
                    logging.debug("\t'%s' startswith '%s'", a, b)
                    return True
                elif b.startswith(a):
                    logging.debug("\t'%s' startswith '%s'", b, a)
                    return True
                elif a_reversed.startswith(b):
                    logging.debug("\t'%s' reverse startswith '%s'", a, b)
                    return True
                elif b_reversed.startswith(a):
                    logging.debug("\t'%s' reverse startswith '%s'", b, a)
                    return True

            # fuzzy comparizon, based on token_sort_ratio (others are not accurate)
            score = token_sort_ratio(a, b)
            if score >= OPTION_MATCH_APPROX_RATIO:
                print("\t'%s' ~ '%s' (score: %d)" % (a, b, score))
                return True

    # no match
    return False


def group_keys(mappings, key1, key2, group1, group2):
    """
    Return a string containing the name of the group containing the keys.

    Add the keys to a group into mappings['groups'][selected_group_name]
    and set the vcard group in mappings['vcard_group'][key]
    """

    if not isinstance(mappings, dict):
        raise TypeError("parameter 'mappings' must be a dict (type: '" + str(type(mappings)) + "')")
    if not isinstance(key1, str):
        raise TypeError("parameter 'key1' must be a string (type: '" + str(type(key1)) + "')")
    if not isinstance(key2, str):
        raise TypeError("parameter 'key2' must be a string (type: '" + str(type(key2)) + "')")
    if not isinstance(group1, str) and group1:
        raise TypeError("parameter 'group1' must be a string or None(type: '" + str(type(group1)) + "')")
    if not isinstance(group2, str) and group2:
        raise TypeError("parameter 'group2' must be a string or None(type: '" + str(type(group2)) + "')")

    logging.debug("\t\t\tgrouping '%s' (g: %s) and '%s' (g: %s)", key1, group1, key2, group2)

    selected_group = group1

    # if grouping is realy required
    if key1 != key2 and (group1 != group2 or (not group1 and not group2)):

        # first match (no existing group for both vcards)
        if not group1 and not group2:
            # create a group
            new_group_key = select_most_relevant_name([key1, key2])
            if new_group_key in mappings['groups']: # should not happen
                raise RuntimeError("Failed to group keys: a group already exists with name '" + new_group_key + "'")
            mappings['groups'][new_group_key] = [key1, key2]
            selected_group = new_group_key
            logging.debug("\t\t\tcreated new group '%s' with %s", selected_group, mappings['groups'][selected_group])

        # one vcard needs to join the other one's group
        elif (group1 and not group2) \
        or (not group1 and group2):
            exiting_group = group1 if group1 else group2
            vcard_to_add = key2 if group1 else key1

            # added vard to existing group
            logging.debug("\t\t\tgroup '%s' before: %s", exiting_group, mappings['groups'][exiting_group])
            logging.debug("\t\t\tadded vcard '%s' to group '%s'", vcard_to_add, exiting_group)
            mappings['groups'][exiting_group].append(vcard_to_add)
            logging.debug("\t\t\tgroup '%s' is now: %s", exiting_group, mappings['groups'][exiting_group])

            # update the group key
            selected_group = exiting_group
            new_group_key = select_most_relevant_name([exiting_group, vcard_to_add])
            if new_group_key != exiting_group and OPTION_UPDATE_GROUP_KEY:
                mappings['groups'][new_group_key] = mappings['groups'][exiting_group]
                del mappings['groups'][exiting_group]
                for k in mappings['groups'][new_group_key]:
                    mappings['vcard_group'][k] = new_group_key
                selected_group = new_group_key
                logging.debug("\t\t\tupdated group '%s' to '%s'", exiting_group, new_group_key)

        # need to merge the two groups, if not already in the same group
        elif group1 != group2:
            # select the destination group key1
            dest_group_key = select_most_relevant_name([group1, group2])
            other_group_key = group1 if dest_group_key != group1 else group2
            # merge/move the other group into the selected one
            logging.debug("\t\t\told group: %s", mappings['groups'][other_group_key])
            for k in mappings['groups'][other_group_key]:
                mappings['vcard_group'][k] = dest_group_key
                mappings['groups'][dest_group_key].append(k)
            del mappings['groups'][other_group_key]
            selected_group = dest_group_key
            logging.debug("\t\t\tnew group: %s", mappings['groups'][selected_group])
            logging.debug("\t\t\tmerged group '%s' into '%s'", other_group_key, dest_group_key)

    # ensure the vcard group are up to date with the right vcard group
    mappings['vcard_group'][key1] = selected_group
    mappings['vcard_group'][key2] = selected_group

    return selected_group


def get_vcards_groups(vcards):
    """
    Return a list of vcard groups containing vcard keys for vcard that match each others.
    """

    if not isinstance(vcards, dict):
        raise TypeError("parameter 'vcards' must be a dict (type: '" + str(type(vcards)) + "')")

    mappings = {\
         'groups': {} \
        ,'vcard_group': {} \
        ,'attributes': {}
    }

    number_of_vcards = len(vcards)
    logging.info("Grouping '%d' vCards (safely) ...", number_of_vcards)
    logging.info("Using following attributes: %s", ', '.join(OPTION_MATCH_ATTRIBUTES))
    for key, vcard in vcards.items():

        logging.debug("\t'%s' (%s) ...", vcard.fn.value, key)
        vcard_group = mappings['groups'][key] if key in mappings['groups'] else None

        # for every attribute that should be used in the matching process
        for a in OPTION_MATCH_ATTRIBUTES:
            a_key = a.rsplit('_')[0] if '_' in a else ('tel' if a == 'mobiles' else a)
            a_type = a.rsplit('_')[1] if '_' in a else None
            a_values = collect_values(vcard, a)

            # if the vcard has this attribute
            if a_values:

                # if the attribute has not already been collected
                if not a_key in mappings['attributes']:
                    mappings['attributes'][a_key] = {}

                # map each of its values
                for a_value in a_values:

                    # new value
                    if not a_value in mappings['attributes'][a_key]:
                        mappings['attributes'][a_key][a_value] = [key]
                        logging.debug("\t\t\tnew [%s][%s] = '%s'", a_key, a_value, key)

                    # value exists and new key
                    elif not key in mappings['attributes'][a_key][a_value]:
                        logging.debug("\t\t\texisting [%s][%s]", a_key, a_value)

                        if not mappings['attributes'][a_key][a_value]: # should not happen
                            raise RuntimeError("Failed to map attribute '" + a_key + "' with value '" + str(a_value) + "' for key '" + key + "' : empty mapped vcard list")

                        # add the key to the list for this value
                        mappings['attributes'][a_key][a_value].append(key)
                        logging.debug("\t\t\tappended '%s' to [%s][%s]", key, a_key, a_value)

                        # get first matching vcard key
                        # (first existing vcard already mapped with this attribute and value)
                        # note: first one because they should all have the same group
                        #       except the last one that is the vcard that we've just added
                        matched_vcard_key = mappings['attributes'][a_key][a_value][0]
                        logging.debug("\t\t\tfirst matched vcard key: '%s'", matched_vcard_key)
                        if not matched_vcard_key: # should not happen
                            raise RuntimeError("Failed to map attribute '" + a_key + "' with value '" + str(a_value) + "' for key '" + key + "' : no mapped vcard but value exists")
                        # get its group
                        matched_vcard_group = mappings['vcard_group'][matched_vcard_key] if matched_vcard_key in mappings['vcard_group'] else None
                        logging.debug("\t\t\tmatched vcard group: '%s'", matched_vcard_group)

                        # grouping them
                        vcard_group = group_keys(mappings, key, matched_vcard_key, vcard_group, matched_vcard_group)

                    # both already exists: do nothing
                    #else:
                        #raise RuntimeError("Failed to map attribute '" + a_key + "' with value '" + str(a_value) + "' for key '" + key + "' : already exist")

    # fuzzy search names
    if not OPTION_NO_MATCH_APPROX:
        logging.info("Grouping vcards using fuzzy search on names ...")
        number_of_names = len(mappings['attributes']['names'])
        number_of_comparisons = number_of_names * (number_of_names + 1) / 2
        names_count = 0
        comparisons_count = 0
        percentage = 0
        previous_percentage = 0
        display_every_percentage = 1 if number_of_names > 100000 else (2 if number_of_names > 10000 else (5 if number_of_names > 1000 else (10 if number_of_names > 100 else 20)))
        length_of_names_count = str(len(str(number_of_names)))
        names_to_compare_with = mappings['attributes']['names'].copy()
        logging.info("Comparing '%d' names (%d comparisons to make, takes a few minutes)", number_of_names, number_of_comparisons)
        # for every name
        for name1, keys1 in mappings['attributes']['names'].items():
            # prevent the name from being processed again
            del names_to_compare_with[name1]

            # search for other name matching
            for name2, keys2 in names_to_compare_with.items():
                # if match
                if match_approx(name1, name2):
                    # getting keys and groups
                    key1 = keys1[0]
                    key2 = keys2[0] if not key1 in keys2 else key1
                    group1 = mappings['vcard_group'][key1] if key1 in mappings['vcard_group'] else None
                    group2 = mappings['vcard_group'][key2] if key2 in mappings['vcard_group'] else None
                    # grouping them
                    group_keys(mappings, key1, key2, group1, group2)

                # display progress
                comparisons_count += 1
                percentage = int(comparisons_count * 100 / number_of_comparisons)
                if percentage != previous_percentage:
                    previous_percentage = percentage
                    if percentage == 100 or percentage % display_every_percentage == 0:
                        logging.info(("\t{:>3d}% done\t{:>" + length_of_names_count + "d} names, so far").format(percentage, names_count))

            names_count += 1

    # get the not grouped vcards
    vcards_not_grouped = []
    for k in vcards.keys():
        if not k in mappings['vcard_group']:
            vcards_not_grouped.append(k)
    #vcards_not_grouped = list(filter(lambda k: k in mappings['vcard_group'], vcards.keys()))

    return (mappings['groups'], vcards_not_grouped)

